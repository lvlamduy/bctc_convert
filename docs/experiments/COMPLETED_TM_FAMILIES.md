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

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p45, MBB p46,
  VPB p41, HDB p33, VCB p35, CTG p39, BID p39 và VIB p35. Đã map 35 dòng
  nguồn vào `Tiền mặt bằng VND`, `Tiền mặt bằng ngoại tệ`, chứng từ có giá
  bằng ngoại tệ, vàng tiền tệ/phi tiền tệ, đá quý khác và tổng family tùy đúng
  biến thể nhìn thấy; cả tám phương trình hiện kỳ đóng chính xác.
- **Không có:** Không có bank nào trong tám BCTC annual-2025.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. HDB `1.194.085` được pixel
  và trục số nguồn xác nhận sau khi VietOCR đọc `1.194.005`; dấu gạch hiện kỳ
  của CTG được bind trực tiếp từ ô ảnh rồi chuẩn hóa thành 0.

## 2. Tiền gửi tại NHNN

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p45, MBB p46,
  VPB p41, HDB p33, VCB p35, CTG p39, BID p39 và VIB p35. Đã map 28 dòng,
  gồm VND/ngoại tệ, subtotal NHNN Việt Nam, `Tiền gửi khác` 574 và tổng family;
  mười phương trình subtotal/tổng đóng đúng.
- **Không có:** Không có bank nào trong tám BCTC annual-2025.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Tiền gửi tại ngân hàng
  trung ương Lào/Campuchia được gom vào 574 tại MBB, VCB và BID. BID dùng biến
  thể mỗi jurisdiction lại có nhánh VND/ngoại tệ; graph kết thúc toàn bộ subtree
  rồi mới nhận dòng tổng `123.629.833`. HDB `B.416.558` của VietOCR được pixel
  và trục số nguồn bác bỏ thành `8.416.558`.

## 3. Tiền, vàng gửi tại và cho vay/vay các TCTD khác

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p46, MBB p48,
  VPB p42, HDB p34, VCB p36, CTG p40, BID p39 và VIB p36. Đã map 86 dòng
  tiền gửi không/có kỳ hạn, VND, ngoại tệ, cho vay/vay, dự phòng và chiết
  khấu/tái chiết khấu; 33 phương trình cha–con, subtotal và tổng family đóng
  đúng. Dự phòng tổng tại MBB, VCB và BID được map vào ReportNormId 5718.
- **Không có:** Không có bank nào trong tám BCTC annual-2025.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Các ô `-` hiện kỳ của ACB
  được bind trực tiếp từ pixel và chuẩn hóa thành 0. HDB `27.921.364` của
  VietOCR được ảnh gốc, trục số nguồn và phương trình bác bỏ thành
  `27.921.384`.

## 4. Chứng khoán kinh doanh

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p47, MBB p49,
  VPB p43, HDB p34, VCB p37, CTG p41 và BID p40. Đã map 58 dòng chứng khoán
  nợ/vốn, nhánh tổ chức phát hành, khoản khác, tổng và dự phòng; 21 phương
  trình cha–con, gross–dự phòng–net đóng chính xác. HDB là biến thể sparse chỉ
  có chứng khoán nợ; dấu `-` hiện kỳ của nhánh TCTD được bind từ pixel và
  chuẩn hóa thành 0.
- **Không có trong BCTC annual-2025 đã bind:** VIB. VIB có family riêng
  `Chứng khoán đầu tư sẵn sàng để bán`, không bị relabel thành trading.
- **Còn thiếu:** Không còn khoản mục trading chờ map. Bốn bảng tình trạng
  niêm yết tại ACB p48, MBB p50, HDB p34 và CTG p42 là các view phụ không cộng
  thêm, đã được giữ làm đối chứng chống double count.

## 5. Công cụ tài chính phái sinh và tài sản/công nợ tài chính khác

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p49, MBB p66,
  VPB p44, HDB p35, CTG p42, BID p41 và VIB p37. Đã map 100 giao điểm hàng ×
  trục giá trị hợp đồng/tài sản/công nợ cho kỳ hiện tại và so sánh; 62 phương
  trình cha–con, tài sản cộng công nợ và dòng tiền vào/ra đóng chính xác. Hai
  mươi bốn dấu `-` được bind từ đúng giao điểm hình học hàng–cột rồi chuẩn hóa
  thành 0; ô trống không bị đổi thành 0. Header bốn tầng của MBB được nhận đủ
  `hợp đồng → tài sản → nợ phải trả → giá trị thuần`.
- **Không có trong BCTC annual-2025 đã bind:** VCB. Các dòng tổng/chính sách,
  giá trị hợp lý hoặc kiểm soát rủi ro không bị relabel thành bảng giao dịch.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong family này.

Ghi chú OCR số: MBB `173.426` của VietOCR được pixel, trục số nguồn và phép
`136.362.265 - 136.188.840` xác nhận là `173.425`. Cột giá trị thuần và các
cột dòng tiền vào/ra chỉ dùng kiểm tra vì schema không có trục tương đương.

## 6. Phân tích theo loại hình cho vay

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p50, MBB p51,
  VPB p45, HDB p35, VCB p39, CTG p43, BID p41 và VIB p37. Whole-PDF scan tìm
  đúng một vùng owner–child hoàn chỉnh ở mỗi báo cáo; 44 hàng nguồn đã map vào
  718–726 và 5745. VPB giữ đủ bốn lane tiền/% và `Cấp tín dụng khác` được map
  vào 726; BID nhận biến thể `Các khoản phải thu từ cho thuê tài chính`;
  HDB/CTG nhận nhánh thư tín dụng trả chậm vào `Cho vay khác`.
- **Không có:** Không có bank nào trong tám BCTC annual-2025.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Ba dấu `-` được giữ trạng
  thái nguồn rồi chuẩn hóa thành 0. Tổng so sánh HDB nhìn thấy là `442.484.841`;
  kết quả VietOCR `442.464.841` bị pixel và phép cộng chính xác bác bỏ.

## 7. Phân tích cho vay theo ngành nghề kinh doanh

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p51, MBB p52,
  VPB p47, HDB p37, VCB p40, BID p42 và VIB p38. Whole-PDF scan tìm đúng một
  vùng ở mỗi báo cáo này; 102 dòng nguồn đã được map và 22 trục tiền tệ đóng
  đúng với tổng in. Graph dùng một khung family chung nhưng cho phép tập con,
  thứ tự hàng, nhãn branch, hai/bốn lane và owner-total đứng trước thay đổi.
- **Không có trong báo cáo annual-2025 đã bind:** CTG. Toàn PDF không có vùng
  phân tích cho vay theo ngành; kết luận này chỉ áp dụng cho đúng filing đã bind.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Dòng gộp VCB p40
  `Thương mại, dịch vụ` được giữ nguyên một số nguồn và map vào leaf chuyên
  biệt 6073; không tách giả sang hai leaf thành phần.

## 8. Phân tích chất lượng cho vay

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p50, MBB p51,
  VPB p45, HDB p36, VCB p39, CTG p43, BID p42 và VIB p66. Whole-PDF scan
  tìm đúng một graph `Cho vay khách hàng → năm nhóm chất lượng` ở mỗi báo cáo;
  hai bảng chất lượng chứng khoán gần giống của CTG bị loại đúng bởi owner.
  Đã map 40 dòng nhóm 1–5 và ba dòng margin riêng của ACB/MBB/VPB vào 1944;
  16 phương trình tiền đóng đúng, mười ô % của BID đóng về 100% và ô trống
  trong bảng nhiều cột của VIB không bị đổi thành 0.
- **Không có trong annual-2025:** Không có bank nào; cả tám filing đều có
  family này.
- **Còn thiếu trên annual-2025:** Không còn khoản mục nguồn chưa map. HDB dùng
  tổng `546.370.779 / 431.306.069` của đúng population cho vay khách hàng;
  population thư tín dụng trả chậm kế bên được giữ ngoài core. Mười bốn lỗi
  chữ/dấu của VietOCR được đối chiếu pixel; 86 ô tiền đều khớp ảnh nguồn.

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
`docs/experiments/E-0114-annual-2025-loan-quality-8bank-codex-verified-mapping-v1.json`
và
`docs/experiments/E-0067B-loan-quality-margin-separation-project-owner-v1.json`.

## 9. Phân tích dư nợ theo thời gian/thời hạn gốc

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p50, MBB p51,
  VPB p45, HDB p36, VCB p40, CTG p44, BID p42, VIB p38. Ba hàng `Nợ ngắn
  hạn`, `Nợ trung hạn`, `Nợ dài hạn` đã được map cho cả 8 bank; hai hàng
  margin độc lập của MBB và VPB cũng đã được map. VIB có thêm hai cột tỷ lệ
  phần trăm và cả hai kỳ đều khép đúng 100%.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục mục tiêu chưa map. Các dòng tổng vẫn là
  dòng kiểm tra nguồn, không map thành khoản mục chi tiết. HDB có thêm dân số
  `Thư tín dụng trả chậm có điều khoản trả ngay` đứng ngoài lõi ba kỳ hạn; dòng
  này được xác minh nguồn và dùng để khép tổng lớn nhưng không bị ép vào schema
  kỳ hạn.

Kết quả exact-replay:
`docs/experiments/E-0115-annual-2025-loan-maturity-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại ACB p18, MBB p31, VPB p42, HDB p26, VCB p31,
CTG p39, BID p22 và VIB p33 vẫn giữ nguyên kết quả đã xác minh.

## 10. Phân tích cho vay theo loại hình tiền tệ

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p51 và HDB p37.
  Hai hàng `Cho vay bằng VND` và `Cho vay bằng ngoại tệ` đã map vào 757/758;
  cả hai kỳ và các dòng tổng khép đúng.
- **Không có trong báo cáo:** MBB p51–52, VPB p45–47, VCB p39–40, CTG
  p43–44, BID p41–42 và VIB p37–39. Whole-PDF scan đã kiểm tra tới family kế
  tiếp. Các cặp VND/ngoại tệ gần đó thuộc bảng lãi suất hoặc liên ngân hàng.
- **Còn thiếu:** Không còn khoản mục nguồn cần map. HDB có thêm dân số thư tín
  dụng trả chậm đứng ngoài `Cho vay khách hàng`; dân số này chỉ dùng để khép
  tổng lớn. Hai chữ số VietOCR sai tại HDB được số nguồn, pixel và phương trình
  kế toán sửa thành `418.599.063` và `442.484.841`.

Kết quả exact-replay:
`docs/experiments/E-0116-annual-2025-loan-currency-8bank-codex-verified-mapping-v1.json`.

Lượt tám PDF hiện hành trước đó vẫn giữ kết quả bounded absence E-0064 riêng,
không bị suy rộng sang annual-2025.

## 11. Phân tích dư nợ cho vay theo khu vực địa lý

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p77, MBB p91 và
  VIB p59–60. Một graph chung nhận cả biến thể khu vực theo hàng × family theo
  cột và family theo hàng × khu vực theo cột, kể cả bảng so sánh tiếp trang.
  Đã map `Trong nước` (5752) và `Nước ngoài` (765): 6 khoản mục, 12 ô tiền và
  6 phương trình `trong nước + nước ngoài = tổng Cho vay khách hàng` đều đóng
  đúng. Dấu `-` của ACB và VIB được bind từ đúng ô ảnh rồi chuẩn hóa thành 0.
- **Không có đúng family trong báo cáo annual-2025 đã bind:** VPB, HDB, VCB,
  CTG và BID. VPB p81, HDB p60 và BID p63 có bảng địa lý nhưng population là
  dư nợ rộng hơn `Cho vay khách hàng`; chúng là đối chứng âm và không bị thu
  hẹp ngầm. VCB/CTG không có vùng địa lý đúng family trong toàn PDF.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong family annual-2025.

Kết quả exact-replay:
`docs/experiments/E-0117-annual-2025-loan-geography-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại MBB p52 và VIB p53–54 vẫn giữ nguyên kết quả
đã xác minh riêng.

## 12. Phân tích theo loại hình doanh nghiệp/đối tượng khách hàng

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** MBB p52
  (14 khoản mục), VPB p46 (14), HDB p36 (8), VCB p40 (5), BID p42 (7) và
  VIB p39 (8), tổng cộng 57 khoản mục. Cả sáu tổng nguồn đều khép đúng với
  `Cho vay khách hàng`; 114 ô tiền và 86 ô tỷ lệ được kiểm tra độc lập.
- **Không tìm thấy vùng family hoàn chỉnh trong đúng báo cáo đã bind:** ACB và
  CTG. Đây là kết quả quét toàn PDF, không phải tuyên bố rằng mọi filing của hai
  bank đều không có family.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Dòng VCB p40
  `Hợp tác xã và công ty tư nhân` (`937.036 / 1.371.552`) được map nguyên vẹn
  vào leaf gộp 6074; không phân bổ số nguồn sang 776 và 774.

Kết quả exact-replay:
`docs/experiments/E-0118-annual-2025-loan-enterprise-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó vẫn giữ nguyên như một kết quả riêng, không được
trộn kỳ với annual-2025.

## 13. Dự phòng rủi ro cho vay khách hàng

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p51,
  MBB p53, VPB p48, HDB p38, VCB p41, CTG p44, BID p43 và VIB p39. Đã map
  18 lane cha và 79 dòng biến động gồm đầu năm, trích lập/hoàn nhập, sử dụng,
  chênh lệch tỷ giá/điều chỉnh và cuối năm; cả 18 phương trình roll-forward
  đóng chính xác. ACB/VPB còn map riêng lane dự phòng margin/ứng trước 6061–6065.
- **Không có:** Không có bank nào trong tám filing annual-2025.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Chín dấu `-` được bind từ
  đúng pixel trước khi chuẩn hóa thành 0. MBB `2.476` của VietOCR được pixel và
  trục số PaddleOCR6 bác bỏ thành `2.478`; các cột tổng, Việt Nam/nước ngoài và
  dự phòng thư tín dụng trả chậm chỉ làm đối chứng, không cộng trùng.

Kết quả exact-replay:
`docs/experiments/E-0119-annual-2025-provision-movement-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại ACB p18, MBB p34, VPB p45, HDB p28, VCB p31,
CTG p39, BID p23 và VIB p34 vẫn được giữ riêng; VPB của lượt đó là Q1/2026 và
không bị relabel thành Q2.

## 14. Hoạt động mua nợ

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** MBB p54,
  VPB p49, HDB p39 và VIB p40. Đã map 15 dòng `Mua nợ bằng VNĐ`, `Dự phòng
  rủi ro`, `Nợ gốc đã mua` và dòng lãi khi nguồn có trình bày; 30 ô số, 16
  phương trình lõi và ba phương trình nhánh đều đóng chính xác.
- **Không có trong báo cáo annual-2025 đã bind:** ACB, VCB, CTG và BID.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. HDB không in dòng lãi
  riêng nên graph chấp nhận biến thể gốc-only, không tự tạo dòng 5739. MBB và
  VPB có một ô lãi `-`; ba ô so sánh của HDB cũng là `-`; cả năm ô chỉ được
  chuẩn hóa 0 sau khi bind ảnh. Nhánh chất lượng/biến động dự phòng và khối
  lịch sử 2017 của VIB chỉ làm kiểm tra, không cộng trùng.

Kết quả exact-replay:
`docs/experiments/E-0120-annual-2025-purchased-debt-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó vẫn giữ nguyên như kết quả kỳ riêng; VPB của lượt
đó là Q1/2026 và không bị relabel thành annual-2025.

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

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p62,
  MBB p65, VPB p60–61, HDB p45, VCB p53, CTG p52, BID p51 và VIB p46–47.
  Whole-PDF graph tìm đúng một vùng ở từng báo cáo. Đã xác minh 159 mapping và
  43 phương trình trên đúng trục 31/12/2025; trục 31/12/2024 chỉ làm đối chứng.
  Các biến thể gồm bảng tiền tệ theo hàng/cột, savings lồng trong no-term/term,
  bảng đối tượng tiếp trang và bảng tiền/% song song. HDB `985.313` và `95.596`
  được quyết định bằng pixel + PP-OCR + phương trình, không dùng chuỗi số
  VietOCR làm authority.
- **Không có trong annual-2025:** Không có; cả tám filing đều có một vùng duy
  nhất.
- **Có nhưng còn khoản mục chưa map:** BID p51 còn hai dòng gộp: `Công ty cổ
  phần` không cho phép tách vào 1081/1082; `Doanh nghiệp tư nhân, cá nhân`
  không cho phép chia số in vào 1083/1089. Hai dòng giữ `UNRESOLVED` nhưng vẫn
  tham gia kiểm tra tổng bảng.

Kết quả exact-replay annual-2025:
`docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json`.

## 16. Chứng khoán đầu tư

- **Đã xác minh trên BCTC hợp nhất kiểm toán năm 2025:** ACB p52–53, MBB
  p54–56, VPB p50–52, HDB p39–40, VCB p42–43, CTG p45–46, BID p44–45 và
  VIB p40–41. Whole-PDF scan tìm đúng một family ở mỗi báo cáo; 112 mapping,
  224 ô hiện tại–so sánh và 72 phương trình cha–con/gross–dự phòng–net đã được
  kiểm tra độc lập. Mười tám dấu `-` chỉ được chuẩn hóa thành 0 sau khi bind
  đúng ô ảnh.
- **Không có:** Không có bank nào trong tám BCTC annual-2025 vắng toàn bộ
  family này.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. MBB p54 giữ nguyên dòng
  gộp `Trái phiếu Chính phủ và trái phiếu Chính phủ bảo lãnh` tại 807. HDB p39
  cộng có kiểm soát `Tín phiếu NHNN` với `Chứng khoán Chính phủ` theo từng kỳ
  vào 831; các thành phần nguồn vẫn được lưu riêng để replay.

Tại VIB annual-2025, hai dòng TCTD được cộng có kiểm soát một lần vào 808:
`12.104.102 + 28.252.422 = 40.356.524` và
`12.712.080 + 27.150.253 = 39.862.333`.

Kết quả exact-replay:
`docs/experiments/E-0121-annual-2025-investment-securities-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại ACB p19, MBB p35–36, VPB p47–48, HDB p29,
VCB p32, CTG p40, BID p23 và VIB p36 vẫn giữ nguyên 99 mapping/198 ô/39
phương trình. VPB của lượt đó là Q1/2026; BID dùng đơn vị cấp tài liệu và VIB
gộp đúng hai dòng TCTD vào 808.

## 17. Các khoản đầu tư dài hạn khác

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p54,
  MBB p57, VPB p52, HDB p41, VCB p44–45, CTG p47, BID p45 và VIB p41.
  Whole-PDF scan tìm đúng một vùng family trong mỗi báo cáo; 28 mapping/56 ô
  hiện tại–so sánh và 11 phương trình chi tiết–subtotal hoặc
  gross–dự phòng–net đóng chính xác.
- **Biến thể đã đóng:** ACB có summary rồi bảng niêm yết/chưa niêm yết; MBB
  tách tổ chức/dự án và quỹ đầu tư; VPB chỉ có bảng chi tiết ba tổ chức;
  HDB có summary rồi lặp owner ở bảng công ty liên kết; VCB tách liên doanh và
  liên kết qua hai trang; CTG có dự phòng hiện kỳ là dấu `-`; BID có đủ liên
  doanh/liên kết/khác/dự phòng; VIB in hai giá trị dự phòng trước nhãn. Các
  detail row không bị cộng trùng với parent.
- **Không có:** Không có bank nào trong tám BCTC annual-2025 vắng family này.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng annual-2025.
  CTG `-` được bind đúng ô và chuẩn hóa thành 0; dấu `-` so sánh của công ty
  CAEX tại VPB chỉ tham gia phương trình subtotal, không sinh leaf schema giả.

Kết quả exact-replay:
`docs/experiments/E-0122-annual-2025-long-term-investments-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại ACB p19, MBB p36, VPB p48, HDB p30, VCB p33,
CTG p40, BID p24 và VIB p36 vẫn giữ nguyên 29 mapping/58 ô/9 phương trình;
VPB của lượt đó là Q1/2026 và không bị relabel thành annual-2025.

## 18. Tăng, giảm tài sản cố định hữu hình

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p55,
  MBB p58, VPB p53, HDB p41, VCB p48, CTG p48, BID p47 và VIB p42. Một graph
  chung tìm đúng một vùng hoàn chỉnh trên toàn bộ mỗi PDF; 105 mapping và 32
  phương trình nguyên giá, hao mòn lũy kế và giá trị còn lại đóng chính xác.
  Các dòng tăng/giảm tổng, mua mới, XDCB hoàn thành, phân loại lại, thanh lý,
  tăng/giảm khác, chênh lệch tỷ giá và điều chỉnh kiểm toán chỉ xuất hiện khi
  nguồn có in, không bị bắt buộc cho mọi bank.
- **Không có:** Không có bank nào trong tám BCTC annual-2025 vắng family này.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng annual-2025.
  CTG, BID và VIB có trục nguồn xoay; PP-OCRv6 chạy trên ảnh xoay làm numeric
  challenger. VietOCR đọc thiếu chữ số VIB `164.02`, còn pixel/PP-OCRv6 đọc
  `164.021` và toàn bộ roll-forward chỉ đóng với `164.021`.

Kết quả exact-replay:
`docs/experiments/E-0123-annual-2025-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại MBB p37, VPB p49 và VIB p37 vẫn giữ nguyên
35 mapping/12 phương trình. VPB của lượt đó là Q1/2026; ACB/HDB/VCB/CTG/BID
chỉ là bounded absence trong đúng các filing hiện hành đó, không bị suy rộng
sang annual-2025.

## 19. Tăng, giảm tài sản cố định thuê tài chính

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** Không có bank
  nào có bảng biến động TSCĐ thuê tài chính chi tiết để map.
- **Không có trong báo cáo:** ACB, MBB, VPB, HDB, VCB, CTG, BID và VIB. Graph
  chung quét toàn bộ tám PDF, kể cả các trang xoay và tiêu đề xuống dòng, rồi
  xác nhận 0 complete/0 near giữa biên `TSCĐ hữu hình → TSCĐ vô hình`: ACB
  p55→56, MBB p58→60, VPB p53→54, HDB p41→42, VCB p48→49, CTG p48→49, BID
  p47→48 và VIB p42→43. Ba mươi dòng tên công ty, chính sách, cho vay hoặc thu
  nhập cho thuê tài chính chỉ là đối chứng âm, không được nâng thành 896–912.
- **Còn thiếu:** Không có khoản mục nguồn chờ map trong tám filing annual-2025.

Kết quả exact-replay:
`docs/experiments/E-0124-annual-2025-leased-fixed-assets-8bank-bound-report-absence-v1.json`.

Kết quả trên tám filing hiện hành trước đó vẫn được giữ nguyên tại E-0070;
việc thêm schema ngoài family không làm thay đổi snapshot Q2/2026 và VPB
Q1/2026 đó.

## 20. Tăng, giảm tài sản cố định vô hình

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p56,
  MBB p60, VPB p54, HDB p42, VCB p49, CTG p49, BID p48 và VIB p43. Một graph
  chung tìm đúng một vùng hoàn chỉnh trên toàn bộ mỗi PDF; 107 mapping và 32
  phương trình nguyên giá, hao mòn lũy kế và giá trị còn lại đóng chính xác.
  ReportNormId 6069 `Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử
  dụng` được xác minh tại cả tám bank; ba số nằm trong câu thuyết minh vẫn được
  trích theo cùng rule chung, không có parser riêng theo bank.
- **Không có:** Không có bank nào trong tám BCTC annual-2025 vắng family này.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng annual-2025.
  CTG VietOCR đọc tổng giảm nguyên giá là `(65.998)`, còn pixel, trục số nguồn
  và phương trình cùng xác nhận `(85.998)`; giá trị map là `-85.998`.

Kết quả exact-replay:
`docs/experiments/E-0125-annual-2025-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json`.

Lượt BCTC hiện hành trước đó tại MBB p39, VPB p50 và VIB p38 vẫn giữ nguyên
32 mapping/12 phương trình; MBB p40 vẫn chỉ là vùng so sánh. ACB/HDB/VCB/CTG/
BID vẫn là bounded absence trong đúng các filing hiện hành đó, và VPB vẫn là
Q1/2026. Schema 6068/6069 cùng snapshot family cũ được giữ byte-exact khi các
family khác tiếp tục bổ sung schema.

## 21. Tăng, giảm bất động sản đầu tư

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p57 và
  MBB p61. Một graph chung quét toàn bộ từng PDF và chọn đúng hai vùng duy
  nhất. 18 mapping và 27 phương trình nguyên giá, hao mòn lũy kế, giá trị còn
  lại và tổng cột tài sản đóng chính xác; không còn dòng nguồn chưa map.
- **Biến thể đã đóng:** ACB trình bày hai bảng anh em `cho thuê` và `nắm giữ
  chờ tăng giá`; năm tổng family được cộng đúng một lần từ các ô nguồn đã xác
  minh độc lập. Ba ô đầu kỳ của bảng cho thuê là dấu `-`; bbox được suy ra từ
  giao điểm hàng–cột rồi chuẩn hóa 0. MBB có bảng hiện kỳ 2025 và bảng so sánh
  2024 ngay bên dưới; chỉ bảng 2025 được map, còn bảng 2024 là control.
- **Không có bảng biến động chi tiết trong báo cáo annual-2025:** VPB, HDB,
  VCB, CTG, BID và VIB. Biên `TSCĐ vô hình → Tài sản Có khác` cùng whole-PDF
  scan xác nhận bounded absence; policy/statement/near-text không bị relabel.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong hai vùng annual-2025.

Kết quả exact-replay:
`docs/experiments/E-0126-annual-2025-investment-property-8bank-codex-verified-mapping-v1.json`.

Lượt hiện hành trước đó tại MBB p41 vẫn giữ nguyên 9 mapping/11 phương trình;
ACB/VPB/HDB/VCB/CTG/BID/VIB vẫn chỉ là bounded absence trong đúng các filing
Q2/2026 hoặc VPB Q1/2026 đã bind, không bị suy rộng sang annual-2025.

## 22. Tài sản Có khác

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p58–60,
  MBB p62–63, VPB p55–57, HDB p42–44, VCB p50–52, CTG p50–51, BID p49–50
  và VIB p44–45. Whole-PDF graph chung tìm đúng một vùng ở cả tám báo cáo;
  134 mapping/295 ô nguồn và 66 phương trình cha–con, subtotal, lãi phí,
  XDCB, chất lượng và tổng family đóng chính xác.
- **Không có cụm này trong báo cáo annual-2025:** Không có; cả tám bank đều có
  đúng một vùng đầy đủ.
- **Có nhưng còn khoản mục chưa map:** 35 dòng nguồn dưới đây được giữ
  `UNRESOLVED`; không ép các khái niệm gộp, deferred tax, tài trợ thương mại
  hoặc dự phòng vào leaf gần nhất.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 58 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp hai khái niệm 975/970, không có phân bổ nguồn. |
| ACB | 58 | Phải thu Ngân sách Nhà nước | Không nói đây là thuế nộp thừa/được khấu trừ để map 974. |
| ACB | 59 | Tài sản thuế thu nhập doanh nghiệp hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| ACB | 59 | Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm | Ô so sánh là dấu gạch chưa có bbox số độc lập. |
| ACB | 60 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| MBB | 62 | Phải thu liên quan đến tài trợ thương mại | Chưa có leaf tương đương; ô hiện kỳ là dấu gạch. |
| MBB | 62 | Các khoản phải thu miễn truy đòi theo bộ chứng từ | Ô so sánh là dấu gạch chưa có bbox số độc lập. |
| MBB | 62 | Các khoản tạm ứng và đặt cọc hợp đồng | Một dòng gộp 975/973, không có phân bổ nguồn. |
| MBB | 62 | Dự phòng phí và dự phòng bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có leaf tương đương. |
| MBB | 62 | Lãi phải thu hoạt động tín dụng và phí phải thu | Dòng gộp lãi tín dụng và phí, không thu hẹp vào 983. |
| MBB | 63 | Lợi thế thương mại | Ô hiện kỳ là dấu gạch chưa có bbox số độc lập. |
| MBB | 63 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| VPB | 55 | Phải thu bán tài sản tài chính | Rộng hơn 976 `Phải thu từ bán chứng khoán`. |
| VPB | 55 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có leaf tương đương. |
| VPB | 55 | Nợ đủ tiêu chuẩn | Ô so sánh là dấu gạch chưa có bbox số độc lập. |
| VPB | 56 | Tài sản có khác | Ô so sánh là dấu gạch chưa có bbox số độc lập. |
| VPB | 56 | Lợi thế thương mại | Ô hiện kỳ là dấu gạch chưa có bbox số độc lập. |
| VPB | 57 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| HDB | 42 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| HDB | 43 | Phải thu từ thanh lý TSCĐ | Ô hiện kỳ là dấu gạch và chưa có leaf chính xác. |
| HDB | 44 | Dự phòng rủi ro các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| VCB | 50 | Phải thu từ ngân sách Nhà nước về hỗ trợ lãi suất | Là phải thu ngân sách, không phải phải thu NHNN 979. |
| VCB | 51 | Tài sản thuế thu nhập hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| VCB | 51 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| CTG | 50 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| CTG | 50 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| BID | 49 | Các khoản phải thu khác | Parent gộp phải thu nội bộ và bên ngoài, không phải leaf hẹp 981. |
| BID | 49 | Tài sản thuế thu nhập doanh nghiệp hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| BID | 49 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| BID | 49 | Phải thu trong nghiệp vụ tài trợ thương mại | Chưa có leaf tương đương. |
| VIB | 44 | Phải thu từ Ngân sách Nhà nước | Không đủ nghĩa để map vào 974 hoặc 979. |
| VIB | 44 | Phải thu từ hoạt động tài trợ thương mại | Chưa có leaf tương đương. |
| VIB | 44 | Phải thu hoa hồng bảo hiểm | Không xác định đối tác là công ty bảo hiểm con như 978 yêu cầu. |
| VIB | 44 | Tài sản thuế TNDN hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| VIB | 44 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Ô hiện kỳ là dấu gạch và chưa có nhánh dự phòng chính xác. |

Kết quả exact-replay:
`docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json`.

- **Lượt hiện hành trước đó — đã xác minh:** MBB p42, VPB p51–53 và VIB p39.
  Đã map 58 khoản mục
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

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p60,
  MBB p63, VPB p58, HDB p44, VCB p52, CTG p51, BID p50 và VIB p45.
  Whole-PDF graph tìm đúng một vùng ở từng báo cáo. Đã xác minh 47 mapping,
  101 ô giá trị và 46 phương trình cho tổng family, vay NHNN, tiền gửi Kho bạc,
  tiền gửi Bộ Tài chính, tiền tệ, kỳ hạn và các nhánh vay chi tiết. Sáu dấu `-`
  được bind đúng ô ảnh rồi chuẩn hóa thành 0. Giá trị so sánh `1` của HDB hiện
  rõ trên PDF nhưng quá nhỏ nên detector không tách thành line; verifier bind
  trực tiếp crop RGB của ô số đó trước khi đưa vào phương trình.
- **Không có cụm này trong báo cáo annual-2025:** Không có; cả tám bank đều có
  một vùng duy nhất.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Theo quyết định của chủ dự
  án, repo ACB/CTG và hai khoản vay đặc thù của BID được gom có kiểm soát vào
  1033 `Vay khác`; các thành phần nguồn vẫn được lưu riêng, không bị mất dấu.

Kết quả exact-replay:
`docs/experiments/E-0128-annual-2025-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json`.

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

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p63,
  MBB p66, VPB p62, HDB p45, VCB p53, CTG p53, BID p51 và VIB p47. Matcher
  dùng cùng một owner/child/period/unit graph và tìm đúng một vùng trong mỗi
  PDF; biến thể owner không có số note và dòng con bắt đầu bằng `Vốn tài trợ`
  được nhận bằng rule chung. Đã xác minh 20 mapping, 40 ô giá trị và 8 phương
  trình. ACB tách JBIC thành VND/ngoại tệ; CTG tách VND/ngoại tệ; HDB khép ba
  chương trình con vào nhánh ngoại tệ; BID giữ nguyên dòng gộp vàng + ngoại tệ
  và map một lần vào 1099 `Khác`. Dấu `-` hiện kỳ của VCB được bind đúng crop
  ảnh rồi mới chuẩn hóa thành 0.
- **Không có trong annual-2025:** Không có; cả tám filing đều có đúng một vùng.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong family annual-2025.

Kết quả exact-replay:
`docs/experiments/E-0130-annual-2025-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json`.

Lượt hiện hành trước đó vẫn giữ kết quả riêng tại MBB p43, VPB p56 và VIB p42
(6 mapping/4 phương trình); ACB/HDB/VCB/CTG/BID là bounded absence chỉ trong
đúng các filing hiện hành đã bind. VPB giữ đúng nguồn Q1/2026.

## 25. Phát hành giấy tờ có giá

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p63,
  MBB p66, VPB p62, HDB p46, VCB p54, CTG p53–54, BID p52 và VIB p47.
  Whole-PDF matcher tìm đúng một vùng ở cả 8/8 bank. Rule chung nhận kỳ hạn
  viết bằng chữ của ACB và ghép trang CTG `(TIẾP THEO)` chỉ khi hai trang liền
  nhau giữ cùng tập công cụ/kỳ hạn; bank/page không tham gia quyết định. Đã
  xác minh 70 mapping, 188 thành phần giá trị và 34 phương trình. Mười một ô
  `-` của CTG/VIB được bind từ pixel trước khi chuẩn hóa 0. Tổng đầu năm HDB
  là `81.349.744`; VietOCR đọc nhầm `31.349.744` nên bị loại bằng pixel,
  PP-OCRv6 và phương trình kế toán.
- **Không có trong annual-2025:** Không có; cả tám filing đều có đúng một vùng.
- **Còn thiếu trên annual-2025:** 5 dòng nguồn:

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 62 | Toàn family — Dưới 12 tháng | Bảng kỳ hạn áp dụng cho tổng chứng chỉ tiền gửi + trái phiếu, không có phân bổ theo công cụ. |
| VPB | 62 | Toàn family — Từ 12 tháng đến dưới 5 năm | Cùng một trục toàn-family; không tự chia vào các leaf của từng công cụ. |
| VPB | 62 | Toàn family — Từ 5 năm trở lên | Cùng một trục toàn-family; không tự chia vào các leaf của từng công cụ. |
| HDB | 46 | Chi phí phát hành (`(74.995)` / `(35.706)`) | Dòng contra đã tham gia phương trình giá trị thuần nhưng schema chưa có leaf chi phí phát hành riêng. |
| VCB | 54 | Trung, dài hạn bằng ngoại tệ (`14` / `14`) | Một số nguồn gộp trung hạn và dài hạn, không có căn cứ phân bổ sang 1115/1116. |

Kết quả exact-replay annual-2025:
`docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json`.

- **Lượt hiện hành đã xác minh trước đó:** ACB p21, MBB p44, VPB p56, HDB p31, VCB p35, CTG p42,
  BID p25 và VIB p43. Whole-PDF scan tìm đúng một vùng hoàn chỉnh trên mỗi
  bank. Đã map 71 khoản mục/132 thành phần giá trị và kiểm tra 36 phương trình
  theo công cụ, kỳ hạn và tổng family. CTG dùng biến thể kỳ hạn theo hàng × công
  cụ theo cột; bốn ô dấu `-` được khóa trực tiếp bằng pixel và chuẩn hóa thành
  0. ACB chỉ dùng cột giá trị ghi sổ để map, cột mệnh giá làm đối chứng. VCB
  dùng nhánh gộp `Kỳ phiếu, trái phiếu`; VPB giữ đúng nguồn Q1/2026. Mốc đúng
  5 năm của ACB được nhận vào leaf 1103/1111 có biên trên bao gồm 5 năm. MBB
  giữ hai hàng trái phiếu riêng: `Dưới 5 năm` map 6010 và `Trên 5 năm` map
  1112. Vì PDF không tách số `Dưới 5 năm` thành `Dưới 12 tháng` và `Từ 12
  tháng đến 5 năm`, hệ thống không tự bịa phép chia nhỏ hơn. Dòng `Chứng chỉ
  tiền gửi — Trên 12 tháng` map nguyên vẹn vào 6009; đây cũng là leaf rộng đã
  có trong schema. Trái phiếu tăng vốn BIDV map riêng vào 1117 và vẫn là
  detail không cộng lặp với parent trái phiếu.
- **Cấu trúc schema hiện hành:** 1100 là root; 1101 `Chứng chỉ tiền gửi`, 1105
  `Kỳ phiếu`, 1109 `Trái phiếu`, 1113 `Tổng kỳ phiếu và trái phiếu` và 1117
  `Các loại giấy tờ có giá khác (bao gồm trái phiếu tăng vốn)` là các nhánh
  công cụ. Các leaf 1103/1107/1111/1115 dùng biên `Từ 12 tháng đến 5 năm`
  (bao gồm đúng 5 năm); 1104/1108/1112/1116 là `Trên 5 năm`. Hai leaf nguồn
  rộng 6009 `Trên 12 tháng` và 6010 `Dưới 5 năm` được giữ để nhận đúng các
  bảng không in chi tiết hơn.
- **Không có cụm này trong các báo cáo hiện hành đã bind:** Không có; cả 8 bank đều có đúng một vùng.
- **Còn thiếu ở lượt hiện hành:** Chỉ còn ba hàng VPB dưới đây. Đây là trục kỳ hạn của toàn cụm,
  không chỉ rõ số thuộc chứng chỉ tiền gửi, kỳ phiếu hay trái phiếu.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 56 | Toàn family — Dưới 12 tháng | Trục kỳ hạn áp dụng cho toàn family, không riêng một công cụ. |
| VPB | 56 | Toàn family — Từ trên 12 tháng đến 5 năm | Trục kỳ hạn toàn family, không riêng một leaf công cụ. |
| VPB | 56 | Toàn family — Từ trên 5 năm trở lên | Trục kỳ hạn toàn family, không riêng một leaf công cụ. |

## 26. Các khoản phải trả và công nợ khác

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p64,
  MBB p67, VPB p63, HDB p47, VCB p54, CTG p54, BID p52 và VIB p48.
  Whole-PDF matcher tìm đúng một vùng ở cả 8/8 bank. Đã xác minh 53 mapping,
  184 thành phần giá trị và 32 phương trình parent–child/tổng. Ba dấu `-` của
  MBB/CTG được bind từ pixel rồi chuẩn hóa 0. HDB VietOCR đọc sai
  `14.169.816`; pixel, PP-OCRv6 và phương trình chi tiết xác nhận
  `4.169.816`.
- **Không có trong annual-2025:** Không có; cả tám filing đều có đúng một vùng.
- **Còn thiếu trên annual-2025:** 0. Dòng không có leaf riêng được gom vào
  ReportNormId 1127 `Khác`, đồng thời giữ topology non-additive nên không cộng
  lặp với parent nội bộ/bên ngoài đã in.
- **Lượt hiện hành trước:** E-0077 đã xác minh 39 mapping/78 thành phần/28
  phương trình. Theo quyết định chủ dự án, E-0132A đóng OPL-001–OPL-018 vào
  1127 `Khác`; giá trị nguồn cũ không đổi và không cộng lặp parent.

Kết quả annual-2025:
`docs/experiments/E-0132-annual-2025-other-payables-liabilities-8bank-codex-verified-mapping-v1.json`.

Closure lượt hiện hành:
`docs/experiments/E-0132A-other-payables-project-owner-other-closure-v1.json`.

## 27. Vốn và các quỹ

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p65–66,
  MBB p69–70, VPB p66–67, HDB p48–49, VCB p56–57, CTG p55–56, BID p53–54
  và VIB p49–50. Whole-PDF matcher tìm đúng một vùng ở cả 8/8 bank và giữ 23
  vùng gần giống làm đối chứng âm. Xoay toàn trang rồi detect lại CTG/BID/VIB
  trong tọa độ landscape chuẩn giúp xác minh tổng cộng 74 mapping/132 ô số và
  18 phương trình tổng vốn. BID có hai ô cùng một line nhưng word boxes tách
  đúng từng số. HDB VietOCR đọc `835.956`; pixel, PP-OCRv6 và phương trình xác
  nhận `535.956`.
- **Không có trong annual-2025:** Không có.
- **Có cụm nhưng còn khoản mục chưa map:** Bảy dòng nguồn dưới đây chưa có
  leaf số dư vốn tương đương. Không còn bảng nào thiếu numeric authority;
  VietOCR xoay chỉ được dùng cho text/anchor, còn số dựa trên pixel, full-page
  PP-OCRv6 và phép khép tổng.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 66 | Quỹ đầu tư phát triển (`68.758` / `68.758`) | Chưa có leaf số dư vốn tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| HDB | 48 | Cổ phiếu quỹ (`(413.448)` / ô đóng kỳ để trống) | Chưa có leaf số dư vốn tương đương; ô trống không bị đổi thành 0. |
| HDB | 48 | Vốn đầu tư xây dựng cơ bản (`89` / `89`) | Chưa có leaf số dư vốn tương đương. |
| VCB | 56 | Quỹ đầu tư phát triển (`1.357.643` / `9.058.060`) | Chưa có leaf riêng; số vẫn nằm trong subtotal quỹ và tổng vốn đã xác minh. |
| CTG | 55 | Quỹ đầu tư phát triển (`512.455` / `548.467`) | Chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| BID | 53 | Quỹ đầu tư phát triển (`290.036` / `6.903.598`) | Chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| VIB | 49 | Quỹ đầu tư phát triển (`10.556` / `10.556`) | Chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |

- **Lượt hiện hành trước:** E-0078 đã xác minh 65 mapping/131 ô số/20 phương
  trình tại ACB, MBB, VPB, HDB, VCB và CTG; BID/VIB structure-only và mười
  mục CAF-001–CAF-010 còn được giữ trong ledger lịch sử.

Kết quả annual-2025:
`docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json`.

## 28. Thu nhập lãi và các khoản thu nhập tương tự

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p67,
  MBB p72, VPB p68, HDB p49, VCB p57, CTG p57, BID p54 và VIB p50.
  Whole-PDF scan tìm đúng một vùng ở cả 8/8 báo cáo; 55 mapping/110 ô số và
  28 phương trình family/subtotal đều đóng đúng cho năm 2025 và 2024.
- **Biến thể đã đóng:** Sáu bank in tổng family sau các dòng con; MBB/VIB in
  tổng trước. Các nhánh chứng khoán, cho thuê tài chính, bảo lãnh, mua nợ và
  thu tín dụng khác là tùy chọn. MBB có một số nguồn gộp `cho vay khách hàng
  và các TCTD khác`, được map nguyên vẹn một lần vào 6075; HDB có dòng riêng
  `Thu phí nghiệp vụ thư tín dụng (L/C)`, map vào 6076. Không tách giả hai
  khái niệm gộp và không đẩy phí L/C sang leaf lãi khác.
- **Không có trong annual-2025:** Không có; cả 8 bank đều có family.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map; không cần Gemma hoặc
  numeric rescue cho family annual này.
- **Lượt hiện hành trước:** E-0079 vẫn giữ riêng ACB p24, MBB p46, VPB p62,
  HDB p34, VCB p38, CTG p45, BID p28 và VIB p45 với 54 mapping/108 ô số/28
  phương trình. Hai lỗi mất chữ số đầu của VietOCR tại VIB vẫn được giữ làm
  disagreement và bị pixel/trục số nguồn bác bỏ; VPB vẫn đúng phạm vi Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0134-annual-2025-interest-income-8bank-codex-verified-mapping-v1.json`.

## 29. Chi phí lãi và các khoản tương tự chi phí lãi

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p67,
  MBB p72, VPB p68, HDB p49, VCB p58, CTG p57, BID p55 và VIB p50.
  Whole-PDF scan tìm đúng một vùng ở cả 8/8 báo cáo; 40 mapping/80 ô số và
  16 phương trình `bốn dòng con = tổng family` đều đóng đúng cho năm 2025 và
  2024.
- **Biến thể đã đóng:** Sáu bank in tổng family sau các dòng con; MBB/VIB in
  tổng trước. Trục kỳ/đơn vị có thể nằm ngay trên family hoặc được kế thừa từ
  phần đầu cùng bảng. CTG dùng nhãn rút gọn `Lãi tiền gửi`, `Lãi tiền vay`;
  các nhãn này chỉ được nhận khi đồng thời nằm dưới owner chi phí lãi, có đủ
  các dòng anh em, hai trục kỳ, đơn vị và phương trình tổng.
- **Lỗi OCR số đã xử lý:** HDB VietOCR đọc dấu phân cách `26,150.925`; pixel
  và trục số nguồn là `26.150.925`. Hai chuỗi vẫn chuẩn hóa về cùng giá trị
  `26.150.925`, còn proposal thô được giữ nguyên trong evidence.
- **Không có trong annual-2025:** Không có; cả 8 bank đều có family. Dòng
  `Trả lãi tiền thuê tài chính` 1155 không xuất hiện trong tám vùng family đã
  bind; đây là non-observation trong vùng, không phải tuyên bố vắng mặt toàn
  tài liệu.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map.
- **Lượt hiện hành trước:** E-0081 vẫn giữ riêng ACB p24, MBB p46, VPB p62,
  HDB p34, VCB p39, CTG p45, BID p29 và VIB p45 với 40 mapping/80 ô số/16
  phương trình; VPB vẫn đúng phạm vi Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0135-annual-2025-interest-expense-8bank-codex-verified-mapping-v1.json`.

## 30. Thu nhập từ lãi thuần

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p10,
  MBB p13, VPB p12, HDB p10, VCB p11, CTG p11, BID p12 và VIB p11.
  Whole-PDF scan 695 trang tìm đúng một graph báo cáo kết quả hoạt động hợp
  nhất ở mỗi PDF; 8 mapping/16 ô số và 48 đối chiếu statement–TM–công thức
  đều khớp chính xác cho năm 2025 và 2024.
- **Biến thể đã đóng:** Nhãn có thể là `Thu nhập lãi thuần` hoặc `Thu nhập từ
  lãi thuần`; VIB trả hai ô số trước nhãn trong provider order nhưng geometry
  vẫn bind đúng hàng. Các vùng thuyết minh trùng text tại MBB/VIB bị loại vì
  không có heading, trục kỳ, đơn vị và bộ ba thu nhập–chi phí–lãi thuần của
  báo cáo kết quả hoạt động hợp nhất.
- **Không có trong annual-2025:** Không có; cả 8 bank đều có dòng 5985.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Giá trị 5985 đồng thời
  khớp hai dòng statement và hai family TM 1143/1151 đã xác minh ở E-0134/
  E-0135; không dùng VietOCR làm numeric truth.

Kết quả annual-2025:
`docs/experiments/E-0136-annual-2025-net-interest-income-8bank-codex-verified-mapping-v1.json`.

## 31. Thu nhập, chi phí và lãi thuần từ hoạt động dịch vụ

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p67,
  MBB p72, VPB p69, HDB p50, VCB p58, CTG p58, BID p55 và VIB p50.
  Whole-PDF scan 695 trang tìm đúng một vùng ở cả 8/8 báo cáo; 101 mapping,
  202 ô số và 48 phương trình thu–chi–lãi thuần đều đóng đúng cho 2025/2024.
- **Biến thể đã đóng:** Bảy bank có owner lãi thuần bao toàn bảng; ACB trình
  bày hai note anh em `Thu nhập...` rồi `Chi phí...` và đối chiếu net với báo
  cáo kết quả kinh doanh p10. Tổng thu/chi có thể đứng trước hoặc sau children;
  HDB dùng `Chi phí cho hoạt động dịch vụ`; child là tùy chọn và không bị ép
  cùng thứ tự. Expense ACB in số dương được giữ là magnitude rồi trừ khi đóng
  net, không bị hiểu thành thu nhập.
- **Không có trong annual-2025:** Không có; cả 8 bank đều có vùng chi tiết.
- **Còn thiếu:** CTG p58 còn hai hàng nguồn gộp `Thu từ dịch vụ tư vấn, ủy
  thác và đại lý` (`965.390` / `961.413`) và `Chi về dịch vụ tư vấn, ủy thác
  và đại lý` (`(309.758)` / `(195.158)`). Schema chỉ có các leaf tách rời nên
  chưa có căn cứ chia một số nguồn; cả hai vẫn tham gia đúng phương trình parent.
- **Lượt hiện hành trước:** MBB p46, VPB p62 và VIB p45 giữ nguyên 43 mapping/
  86 ô/18 phương trình; ACB/HDB/VCB/CTG/BID là bounded absence chỉ trong các
  filing hiện hành đó, VPB vẫn là Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json`.

## 32. Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p68,
  MBB p73, VPB p69, HDB p50, VCB p59, CTG p58, BID p55 và VIB p51.
  Whole-PDF scan 695 trang tìm đúng một vùng ở cả 8/8 báo cáo; 69 mapping,
  138 ô logic từ 152 thành phần nguồn và 48 phương trình thu–chi–lãi thuần
  đều đóng đúng cho 2025/2024.
- **Biến thể đã đóng:** Tổng thu/chi có thể đứng trước, đứng sau hoặc được suy
  ra chính xác từ các child. Ngoại tệ giao ngay và vàng có thể tách hoặc gộp;
  vàng là nhánh tùy chọn. VCB gộp bán vàng với đánh giá lại vàng, và gộp giao
  dịch phái sinh với đánh giá lại phái sinh; các thành phần được cộng đúng một
  lần. HDB có child phái sinh rút gọn nhưng chỉ được nhận dưới parent ngoại hối.
  MBB dùng `kinh doanh ngoại hối` và dòng gộp `ngoại tệ và vàng` không có cụm
  `giao ngay`; biến thể này được nhận bằng owner, siblings, trục kỳ, đơn vị và
  phương trình đầy đủ, không bằng bank/trang.
- **Không có trong annual-2025:** Không có; cả 8 bank đều có vùng chi tiết.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Năm dấu `-` nhìn thấy ở
  VCB/BID được xác thực từ crop rồi chuẩn hóa thành 0; không có disagreement số
  VietOCR trong các ô không phải DASH.
- **Lượt hiện hành trước:** MBB p47, VPB p63 và VIB p46 giữ nguyên 23 mapping/
  46 ô/18 phương trình. ACB/HDB/VCB/CTG/BID là bounded absence chỉ trong các
  filing hiện hành đó; VPB vẫn là Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0138-annual-2025-fx-gold-activity-8bank-codex-verified-mapping-v1.json`.

## 33. Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p68,
  MBB p73, VPB p70, HDB p50, VCB p59, CTG p58 và BID p56. Whole-PDF scan đủ
  695 trang tìm đúng một vùng ở mỗi filing này; 27 mapping/54 ô số và 14
  phương trình hai kỳ đều đóng chính xác.
- **Biến thể annual-2025 đã đóng:** ACB/VPB/VCB dùng net không nhãn ở cuối;
  MBB/CTG/BID in net có nhãn; BID đặt owner trading dưới umbrella trading +
  investment. Dòng dự phòng có thể xuống dòng hoặc đổi vị trí. HDB không in
  dòng dự phòng, nên graph dùng đúng biến thể `thu nhập + chi phí = lãi thuần`
  thay vì tạo một hàng giả; sáu bank còn lại dùng `thu nhập + chi phí + dự
  phòng = lãi thuần`.
- **Không có trong báo cáo annual-2025:** VIB. Toàn PDF chỉ có hoạt động mua
  bán chứng khoán đầu tư; vùng đó là đối chứng âm và không bị relabel.
- **Còn thiếu annual-2025:** Không còn khoản mục nguồn chưa map trong bảy vùng
  hiện diện; không có disagreement số VietOCR. ReportNormId 1192 `Khác` không
  xuất hiện.
- **Lượt hiện hành trước:** ACB p24, MBB p47, VPB p63, HDB p34, VCB p39,
  CTG p45 và BID p29 giữ nguyên 28 mapping/56 ô/14 phương trình; VIB là bounded
  absence và VPB giữ đúng kỳ Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0139-annual-2025-trading-securities-activity-8bank-codex-verified-mapping-v1.json`.

## 34. Lãi/lỗ thuần từ mua bán chứng khoán đầu tư

- **Đã map/xác minh trên BCTC hợp nhất kiểm toán annual-2025:** ACB p68,
  MBB p73, VPB p70, HDB p50, VCB p59, CTG p59, BID p56 và VIB p51. Whole-PDF
  scan đủ 695 trang tìm đúng một vùng ở cả 8 filing; 32 mapping/64 ô logic từ
  70 thành phần nguồn và 16 phương trình hai kỳ đều đóng chính xác.
- **Biến thể annual-2025 đã đóng:** VCB không in dòng dự phòng nên dùng
  `thu nhập + chi phí = lãi thuần`. MBB in thêm dự phòng góp vốn/đầu tư dài hạn
  6028. VPB tách dự phòng AFS và HTM; VIB tách AFS, HTM chung và HTM cụ thể:
  từng ô nguồn được xác minh rồi mới cộng đúng một lần vào 1196. BID đặt owner
  đầu tư dưới umbrella chứng khoán kinh doanh + đầu tư; ranh giới family chung
  loại ứng viên ô dù và giữ đúng owner con, không dùng bank/trang làm rule.
- **Dấu gạch và số:** 5 dấu `-` nhìn thấy ở ACB/VPB/VIB được crop-authenticate
  rồi chuẩn hóa 0. Không có disagreement số VietOCR; ReportNormId 1197 `Khác`
  không xuất hiện.
- **Không có trong báo cáo annual-2025:** Không bank nào; cả 8 filing đều có
  graph chi tiết duy nhất.
- **Còn thiếu annual-2025:** Không còn khoản mục nguồn chưa map.
- **Lượt hiện hành trước:** ACB p25, MBB p47, VPB p63, HDB p35, CTG p46,
  BID p29 và VIB p46 giữ nguyên 28 mapping/56 ô/14 phương trình; VCB là bounded
  absence và VPB giữ đúng nguồn Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0140-annual-2025-investment-securities-activity-8bank-codex-verified-mapping-v1.json`.

## 35. Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư

- **BCTC hợp nhất kiểm toán annual-2025:** Không bank nào trong ACB, MBB, VPB,
  HDB, VCB, CTG, BID và VIB in một dòng số tổng hợp cho ReportNormId 5990.
  Whole-PDF scan quét đủ 695 trang: 0 complete numeric row, 1 near control.
- **Đối chứng âm BID p56:** Nhãn `Lãi thuần từ mua bán chứng khoán kinh doanh và
  chứng khoán đầu tư` là tiêu đề mục 30. Bên dưới là hai bảng riêng 30.1 và 30.2;
  tiêu đề không có hai giá trị cùng hàng nên không được cộng hai bảng để tạo một
  khoản mục 5990 không được in.
- **Lượt hiện hành trước:** MBB p47 vẫn giữ mapping đã xác minh. Whole-PDF scan
  tìm đúng một dòng tổng hợp có hai giá trị cùng hàng; các phương trình
  `249.524 + 3.587 = 253.111` và `415.700 + 1.295.273 = 1.710.973` đóng đúng.
  ACB, VPB, HDB, VCB, CTG, BID và VIB của lượt đó là bounded absence.
- **Còn thiếu:** Không có dòng nguồn annual-2025 cần map; đây là vắng mặt trong
  tám filing cố định, không phải khẳng định vắng mặt trên mọi kỳ/báo cáo.

Kết quả annual-2025:
`docs/experiments/E-0141-annual-2025-combined-securities-net-8bank-bound-report-absence-v1.json`.

## 36. Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p69, MBB p74,
  VPB p71, HDB p51, VCB p60, CTG p59 và BID p56. Whole-PDF scan quét đủ 695
  trang, tìm đúng một note chi tiết tại mỗi bank này và xác minh 28 mapping/56
  ô số cùng 20 phương trình hai kỳ. Bốn dấu `-` được crop-bind rồi chuẩn hóa 0;
  không có disagreement số VietOCR.
- **Biến thể annual-2025 đã đóng:** ACB tách ba nguồn cổ tức; MBB tách cổ
  tức/lợi tức và lãi bán khoản góp vốn trước tổng; VPB chỉ có một dòng cổ tức;
  HDB cộng cổ tức dài hạn với phần chia lãi theo phương pháp vốn chủ sở hữu;
  VCB có thêm thu nhập thanh lý; BID có nhãn cổ tức xuống dòng nhưng hai ô số
  xen giữa hai fragment. CTG in một dòng gộp `Từ chứng khoán vốn`; dòng này vẫn
  tham gia phương trình nguồn nhưng không bị tách vào hai leaf trading/investment.
- **Không có note chi tiết annual-2025:** VIB. VIB p11 chỉ in aggregate trên
  báo cáo kết quả hoạt động; toàn bộ 78 trang không có note đánh số với trục kỳ,
  đơn vị và graph con nên aggregate không bị relabel thành note chi tiết.
- **Lượt hiện hành trước:** ACB p25, MBB p48, VPB p64, HDB p35, VCB p39,
  CTG p46 và BID p29 giữ nguyên 27 mapping/54 ô/16 phương trình; VIB là bounded
  absence và VPB giữ đúng nguồn Q1/2026.
- **Còn thiếu annual-2025:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| CTG | 59 | Từ chứng khoán vốn (`15.823` / `13.284`) | Một số nguồn gộp chứng khoán vốn kinh doanh và đầu tư; schema 1200/1201 tách hai leaf nên không được tự chia hoặc thu hẹp. Dòng được giữ source-only và vẫn đóng subtotal cổ tức. |

Kết quả annual-2025:
`docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-codex-verified-mapping-v1.json`.

## 37. Chi phí quản lý chung (Chi phí hoạt động)

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p70, MBB p74,
  VPB p72, HDB p51, VCB p61, CTG p60, BID p57 và VIB p52. Whole-PDF scan quét
  đủ 695 trang và tìm đúng một vùng family ở mỗi filing. Pixel, trục số nguồn,
  live schema và 42 phương trình xác minh 103 mapping/206 ô số.
- **Biến thể annual-2025 đã đóng:** parent tổng có thể đứng ở cuối; các nhánh
  nhân viên, tài sản và quản lý có tập con/thứ tự khác nhau; nhãn có thể xuống
  dòng hoặc có `Trong đó`; dòng dự phòng có thể là aggregate, hai component
  chi tiết hoặc chỉ một nhãn chung. Dấu `-` hiện kỳ của VCB được bind rồi chuẩn
  hóa 0. Bốn lỗi số VietOCR tại HDB/CTG/VIB bị pixel, source axis và phương
  trình bác bỏ, không sửa ngầm số nguồn.
- **Không có trong annual-2025:** Không có bank nào; cả tám filing đều có đúng
  một vùng family.
- **Còn thiếu annual-2025:** 14 hàng nguồn có ý nghĩa riêng nhưng schema
  1205–1220 chưa có leaf tương ứng; các hàng vẫn nằm trong phương trình nguồn
  và không bị ép sang leaf gần tên.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 70 | Chi khác (dưới `Chi về tài sản`) | Không có leaf chi phí tài sản khác; không đồng nhất với chi phí quản lý khác. |
| ACB | 70 | Hoàn nhập chi phí dự phòng (tổng) | Aggregate của hai component đã map; giữ source-only để kiểm tra và tránh double count. |
| MBB | 74 | Chi khác về tài sản | Không có leaf chi phí tài sản khác. |
| VPB | 72 | Chi thuê tài sản | Không có leaf chi phí thuê tài sản dưới `Chi về tài sản`. |
| VPB | 72 | Chi phí công nghệ thông tin | Không có leaf chi phí CNTT. |
| VPB | 72 | Chi về thuế GTGT đầu vào không được khấu trừ | Không có leaf VAT đầu vào không khấu trừ. |
| HDB | 51 | Chi thuê tài sản | Không có leaf chi phí thuê tài sản. |
| HDB | 51 | Chi về bảo dưỡng và sửa chữa tài sản | Không có leaf bảo dưỡng/sửa chữa tài sản. |
| HDB | 51 | Chi khác về tài sản | Không có leaf chi phí tài sản khác. |
| HDB | 51 | Chi phí quảng cáo, tiếp thị, khuyến mại | Không có leaf quảng cáo/tiếp thị/khuyến mại. |
| HDB | 51 | Chi phí hội nghị, lễ tân, khánh tiết | Không có leaf hội nghị/lễ tân/khánh tiết. |
| HDB | 51 | Chi phí điện, nước, vệ sinh cơ quan | Không có leaf tiện ích/vệ sinh cơ quan. |
| CTG | 60 | Chi khác (dưới `Chi về tài sản`) | Không có leaf chi phí tài sản khác. |
| CTG | 60 | Chi phí dự phòng | Nhãn nguồn chung không đủ căn cứ thu hẹp vào 1218 hoặc 1220. |

Kết quả annual-2025:
`docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json`.

- **Lượt hiện hành trước:** ACB p25, MBB p48, VPB p65, HDB p35, VCB p40,
  CTG p47, BID p30 và VIB p46 giữ nguyên 99 mapping/198 ô/30 phương trình và
  bốn hàng OPEN; VPB giữ đúng nguồn Q1/2026.

## 38. Chi phí dự phòng rủi ro tín dụng

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p70, MBB p75,
  VPB p73, VCB p61 và VIB p52. Whole-PDF scan quét đủ 695 trang và tìm đúng
  một note chi tiết ở mỗi filing này. Pixel, trục số nguồn, live schema và 12
  phương trình xác minh 25 mapping/50 ô số; không có disagreement số VietOCR.
- **Biến thể annual-2025 đã đóng:** ACB tách dự phòng chung/cụ thể/phải thu khó
  đòi; MBB có cho vay khách hàng, TCTD, mua nợ, cam kết và rủi ro khác; VPB có
  margin/ứng trước và tài sản có rủi ro khác; VCB tách chung/cụ thể cho khách
  hàng và trái phiếu doanh nghiệp chưa niêm yết; VIB dùng parent cho vay khách
  hàng với hai con chung/cụ thể. VPB và VCB cộng các component đã xác minh đúng
  một lần vào 1228 `Dự phòng khác`. Một dấu `-` hiện kỳ của VPB được crop-bind
  trước khi chuẩn hóa thành 0.
- **Không có cụm thuyết minh chi tiết trong annual-2025:** HDB, CTG và BID.
  HDB chỉ có số aggregate trong báo cáo bộ phận/chính sách; CTG chỉ có dòng dự
  phòng chung ở chi phí hoạt động và aggregate KQKD; BID có dòng chi phí hoạt
  động loại trừ dự phòng tín dụng/chứng khoán cùng aggregate KQKD. Không nguồn
  nào đủ cấu trúc để relabel thành note chi tiết 1221.
- **Còn thiếu annual-2025:** Không còn; 0 dòng OPEN.

Kết quả annual-2025:
`docs/experiments/E-0144-annual-2025-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json`.

- **Lượt hiện hành trước:** MBB p49, VPB p66 và VIB p47 giữ nguyên 15
  mapping/30 ô/8 phương trình. E-0100 đóng CRPE-001/002 vào 1228; ACB, HDB,
  VCB, CTG và BID là bounded detailed-note absences; VPB giữ đúng nguồn Q1/2026.

## 39. Thu nhập, chi phí và lãi thuần từ hoạt động khác

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p69, MBB p74,
  VPB p71, HDB p51, VCB p60, CTG p59, BID p56 và VIB p51. Whole-PDF scan
  quét đủ 695 trang và tìm đúng một vùng đầy đủ trong từng filing. Pixel, trục
  số nguồn, live schema và 48 phương trình xác minh 72 mapping/144 ô số;
  không có disagreement số VietOCR và không còn dòng OPEN.
- **Biến thể annual-2025 đã đóng:** tổng thu, tổng chi và lãi thuần có thể có
  hoặc không có nhãn; VIB có số đứng trước nhãn theo provider order; nhánh
  thanh lý tài sản, phạt hợp đồng, hoạt động kinh doanh/tài trợ khác có thể
  tách thành nhiều dòng. Các dòng cùng nghĩa `Khác` chỉ được cộng có kiểm soát
  sau khi từng số nguồn được xác minh và cả ba phương trình thu–chi–net đóng.
  Parent thu/chi vẫn phải có ít nhất một child, trục kỳ và đơn vị; text đơn lẻ
  không đủ quyết định family hay mapping.
- **Không có cụm trong annual-2025:** Không bank nào; cả 8/8 filing có note
  chi tiết duy nhất.
- **Còn thiếu annual-2025:** Không còn; 0 dòng OPEN.

Kết quả annual-2025:
`docs/experiments/E-0145-annual-2025-other-activity-8bank-codex-verified-mapping-v1.json`.

- **Lượt hiện hành trước:** MBB p47, VPB p64 và VIB p46 giữ nguyên 23
  mapping/46 ô/14 phương trình; ACB/HDB/VCB/CTG/BID là bounded detailed-note
  absences trong đúng các filing cũ. E-0100 cộng OACT-001 vào 1239 `Khác`;
  VPB giữ đúng nguồn Q1/2026.

## 40. Chi phí thuế thu nhập doanh nghiệp

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p71, MBB p76,
  VPB p64, HDB p52, VCB p62, CTG p60, BID p57 và VIB p53. Whole-PDF scan
  quét đủ 695 trang và tìm đúng một vùng thuế chi tiết trên cả 8/8 filing.
  Pixel, trục số nguồn, live schema và 32 phương trình xác minh 61 mapping/120
  ô số; không bank nào thiếu family.
- **Biến thể annual-2025 đã đóng:** graph chung nhận nhãn lợi nhuận trước thuế
  dài hoặc ngắn, điều chỉnh tùy chọn, bảng ngân hàng/chi nhánh nước ngoài/công
  ty con, ô so sánh để trống và bảng thuế hoãn lại tách riêng. CTG
  `(370.109]` và VIB `2.40i` là hai lỗi VietOCR được giữ nguyên làm proposal;
  trục số nguồn xác nhận `(370.109)` và `2.401`, rồi các phương trình đóng mà
  không sửa tay hay dùng VietOCR làm numeric truth.
- **Không có cụm trong annual-2025:** Không bank nào.
- **Còn thiếu annual-2025:** bảy dòng nguồn dưới đây vẫn hiển thị và tham gia
  kiểm tra khi cần, nhưng chưa có leaf chính xác hoặc nhãn chưa đủ hẹp:

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 71 | Các khoản điều chỉnh làm tăng/(giảm) thu nhập chịu thuế khác | Nhãn rộng; không ép vào một leaf điều chỉnh cụ thể. |
| ACB | 71 | Hoàn nhập tài sản thuế TNDN hoãn lại | Schema có net thuế hoãn lại nhưng chưa có leaf component nguồn này. |
| ACB | 71 | Chênh lệch tạm thời được khấu trừ | Schema có net thuế hoãn lại nhưng chưa có leaf component nguồn này. |
| MBB | 76 | Thuế TNDN do thoái vốn tại công ty con | Chưa có leaf thuế hiện hành do thoái vốn; ô so sánh để trống và không đổi thành 0. |
| VPB | 64 | Các điều chỉnh khác | Thuộc phần cuốn chiếu thuế phải nộp sau chi phí thuế; chưa có leaf chi phí tương đương, ô so sánh để trống. |
| CTG | 60 | Điều chỉnh khác | Thuộc phần cuốn chiếu thuế phải nộp sau bảng chi phí thuế, không ép vào family chi phí. |
| VIB | 53 | Điều chỉnh khác | Nhãn rộng hơn 5733 về điều chỉnh thuế các năm trước; giữ source-only nhưng dùng trong phương trình tổng đã xác minh. |

Kết quả annual-2025:
`docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json`.

- **Lượt hiện hành trước:** MBB p50, VPB p59 và VIB p48 giữ nguyên 28
  mapping/56 ô/20 phương trình; ACB/HDB/VCB/CTG/BID là bounded detailed-note
  absences trong đúng các filing cũ. VIB `TAX-001` vẫn được giữ nguyên.

## 41. Tiền và các khoản tương đương tiền

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p73, MBB p78,
  VPB p73, HDB p54, VCB p64, CTG p62, BID p58 và VIB p50. Whole-PDF scan
  tìm đúng một vùng family trong cả 8/8 filing; 43 mapping/86 ô số và 18
  phương trình đóng đúng trên đầy đủ family 1248–1254.
- **Không có cụm trong annual-2025:** Không bank nào.
- **Còn thiếu annual-2025:** Không có khoản mục nguồn chưa map. Ba dấu `-`
  nhìn thấy tại ACB, HDB và VPB được bind vào pixel trước khi chuẩn hóa thành
  zero; không ô trống nào bị đổi thành zero.
- **Lượt hiện hành trước:** ACB p8, MBB p50, VPB p66, VCB p40, CTG p47 và
  VIB p45 giữ nguyên 31 mapping/60 ô/12 phương trình. HDB/BID là bounded
  detailed-note absences trong đúng hai filing cũ; VPB là nguồn Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0147-annual-2025-cash-equivalents-8bank-codex-verified-mapping-v1.json`.

## 42. Mua mới và thanh lý các công ty con

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** Không có mapping vì
  cả tám PDF đều không trình bày bảng chi tiết 1255–1258 gồm tổng giá trị giao
  dịch, phần thanh toán bằng tiền và tiền thực có trong công ty con/đơn vị kinh
  doanh.
- **Không có cụm trong annual-2025:** ACB, MBB, VPB, HDB, VCB, CTG, BID và
  VIB. Whole-PDF scan quét đủ 695 trang, trả 0 full match và giữ 25 policy,
  narrative hoặc cash-flow hit làm đối chứng âm.
- **Còn thiếu annual-2025:** Không có khoản mục nguồn chưa map; không narrative
  nào có đủ ba dòng kế toán bắt buộc nên không được relabel thành bảng.
- **Lượt hiện hành trước:** Giữ nguyên tám bounded absences E-0093; HDB/CTG có
  đối chứng giao dịch/cash-flow nhưng vẫn thiếu ba dòng bắt buộc.

Kết quả annual-2025:
`docs/experiments/E-0148-annual-2025-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json`.

## 43. Thu nhập nhân viên của ngân hàng

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p73, VPB p73,
  BID p58 và VIB p54. Whole-PDF scan tìm đúng một vùng family ở mỗi báo cáo;
  18 mapping/36 ô số và 16 phương trình tổng hoặc tỷ lệ đã xác minh.
- **Biến thể đã đóng:** BID dùng nhãn quấn dòng `Tổng số cán bộ, nhân viên bình
  quân trong năm`; VIB trả hai số bình quân trước nhãn. ACB in bình quân
  người/năm: số in được kiểm tra lại bằng tử số/mẫu số, rồi mới chia 12 để map
  1267/1268 theo đơn vị người/tháng (`14.16`/`13.94` và `37.57`/`38.10`).
- **Không có cụm trong annual-2025:** MBB, HDB, VCB và CTG. Policy trợ cấp
  thôi việc hoặc số nhân viên đứng riêng không được relabel thành bảng.
- **Còn thiếu annual-2025:** Không có khoản mục nguồn chưa map.
- **Lượt hiện hành trước:** E-0094/E-0100 giữ riêng ACB p26, VPB p66 và VIB
  p49 với 13 mapping/26 ô/14 phương trình; VPB là nguồn Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0149-annual-2025-employee-income-8bank-codex-verified-mapping-v1.json`.

## 44. Tình hình thực hiện nghĩa vụ với ngân sách nhà nước

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p73, MBB p68,
  VPB p64, HDB p47, VCB p65, CTG p62, BID p52 và VIB p52. Whole-PDF scan tìm
  đúng một vùng family ở cả 8/8 báo cáo; 35 mapping/140 ô logic và 35 phương
  trình cuốn chiếu đóng chính xác.
- **Biến thể đã đóng:** MBB có hai block năm, chỉ block 2025 được lấy; VCB có
  hai cột cuối năm `Phải trả`/`Ứng trước` nhưng map giá trị thuần `Tổng cộng`;
  CTG tách nhánh phải thu và phải trả nên từng ô schema được tính bằng tổng có
  dấu của các ô nguồn đã xác thực; HDB có nhãn `Các loại thuế khác, các khoản
  phí, lệ phí và phải nộp khác` quấn hai dòng, với dấu `-` cuối năm được bind
  pixel rồi chuẩn hóa 0. Numeric challenger sửa lỗi VietOCR HDB `80.055` thành
  số nguồn `60.055`; không sửa số bằng text OCR.
- **Không có cụm trong annual-2025:** Không bank nào.
- **Còn thiếu annual-2025:** Không có khoản mục nguồn chưa map.
- **Lượt hiện hành trước:** E-0095/E-0100 giữ riêng ACB p22, MBB p49, VPB p58,
  HDB p32, CTG p43, BID p26 và VIB p47; VCB là bounded absence, VPB là nguồn
  Q1/2026. HDB `Tiền thuê đất` đã được đưa vào 1279.

Kết quả annual-2025:
`docs/experiments/E-0150-annual-2025-state-budget-obligations-8bank-codex-verified-mapping-v1.json`.

## 45. Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p74, VPB p74,
  HDB p54 và VIB p54. Whole-PDF scan tìm đúng một vùng customer-scoped ở mỗi
  báo cáo này; 25 mapping/50 ô số và 10 phương trình đóng chính xác.
- **Biến thể đã đóng:** ACB giữ `GTCG do doanh nghiệp phát hành` như chi tiết
  không cộng lặp của `Giấy tờ có giá`; HDB dùng trục tương đối `Số cuối năm` /
  `Số đầu năm` và numeric challenger sửa lỗi Transformer `368.639.341` thành
  số pixel/nguồn `388.639.341`; VIB cộng có kiểm soát bốn dòng nguồn vào 1288
  `Khác`. Chỉ nhánh tài sản của khách hàng được lấy; nhánh tài sản của chính
  ngân hàng là đối chứng âm.
- **Không có cụm thuyết minh chi tiết trong annual-2025:** MBB, VCB, CTG và
  BID. Đây chỉ là bounded absence trong đúng filing đã bind.
- **Còn thiếu annual-2025:** Không có khoản mục nguồn chưa map.
- **Lượt hiện hành trước:** E-0096/E-0100 giữ riêng VPB p67, VCB p47 và VIB
  p49 với 15 mapping/30 ô/6 phương trình; VPB là nguồn Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0151-annual-2025-customer-collateral-8bank-codex-verified-mapping-v1.json`.

## 46. Tài sản, giấy tờ có giá của ngân hàng đưa đi thế chấp, cầm cố và chiết khấu

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p74, MBB p78,
  VPB p74, CTG p63 và VIB p54. Whole-PDF scan tìm đúng một vùng family ở mỗi
  báo cáo này; 13 mapping/26 ô số và 10 phương trình child→total đóng chính
  xác.
- **Biến thể đã đóng:** ACB map trực tiếp chứng khoán kinh doanh, chứng khoán
  đầu tư và TSCĐ, còn tiền gửi có kỳ hạn tại TCTD vào 1293 `Tài sản khác`;
  hai dấu `-` được bind pixel rồi chuẩn hóa 0. MBB chỉ có một child `Giấy tờ có
  giá`, đủ unique khi kết hợp owner, hai kỳ và đơn vị. VPB/CTG/VIB cộng có kiểm
  soát toàn bộ các hàng nguồn chưa tách được loại chứng khoán đúng một lần vào
  1293; dấu `-` so sánh của CTG cũng được bind pixel trước khi cộng.
- **Không có cụm thuyết minh chi tiết trong annual-2025:** HDB, VCB và BID.
  Đây chỉ là bounded absence trong đúng filing đã bind.
- **Còn thiếu annual-2025:** Không có khoản mục nguồn chưa map.
- **Lượt hiện hành trước:** E-0097 giữ riêng VPB p67 và VIB p49 với năm
  mapping/10 ô; ba dòng BPA-001–003 cùng hierarchy double-count của VPB vẫn là
  OPEN lịch sử, không bị annual result relabel.

Kết quả annual-2025:
`docs/experiments/E-0152-annual-2025-bank-pledged-assets-8bank-codex-verified-mapping-v1.json`.

## 47. Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra

- **BCTC hợp nhất kiểm toán annual-2025 đã map/xác minh:** ACB p75, MBB p79,
  VPB p75, HDB p55, CTG p63, BID p59 và VIB p55. Whole-PDF scan tìm đúng một
  vùng family ở cả bảy báo cáo; 58 mapping/114 ô số và 46 phương trình đóng
  chính xác.
- **Biến thể đã đóng:** MBB không in family total nhưng có owner và các child
  đầy đủ; HDB dùng `Số cuối năm`/`Số đầu năm`, hai parent trung gian và tiền ký
  quỹ âm; CTG có owner rút gọn `Nghĩa vụ nợ tiềm ẩn và các cam kết`; BID dùng
  parent `Các khoản bảo lãnh`/`Cam kết thanh toán` với hai child L/C; VIB dùng
  ba trục gộp–ký quỹ–thuần và chỉ cột thuần được map. Matcher dừng ở note đánh
  số kế tiếp và cho phép đúng một trang tiếp nối, không dùng bank/page làm rule.
- **Không có bảng chi tiết trong annual-2025:** VCB. p66 chỉ có diễn giải; p67
  đã sang note giao dịch bên liên quan. Đây là bounded absence của bảng chi
  tiết trong đúng filing, không phải khẳng định nguồn rộng hơn không có family.
- **Còn thiếu annual-2025:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 75 | Thư tín dụng trả ngay; Thư tín dụng trả chậm | Schema mới dừng ở parent L/C 1295, chưa có hai leaf theo phương thức thanh toán. |
| ACB | 75 | Trừ: tiền ký quỹ (L/C và bảo lãnh); Bảo lãnh khác chi tiết | Hai dòng ký quỹ là trục khấu trừ; dòng `Bảo lãnh khác` chi tiết trùng tên với parent nguồn, chưa có leaf riêng. |
| VPB | 75 | Trừ: tiền ký quỹ (L/C và bảo lãnh); Cam kết bảo lãnh khác | Các dòng vẫn đóng đúng parent nhưng chưa có leaf/trục khấu trừ tương ứng. |
| VPB | 75 | Hoán đổi lãi suất tiền tệ chéo — nhận/trả; hoán đổi lãi suất một đồng tiền | Schema 1301–1302 chỉ có ngoại hối/hoán đổi tiền tệ, chưa có các leaf hoán đổi lãi suất này. |
| VPB | 75 | Cam kết khác chi tiết; hạn mức tín dụng chưa sử dụng có thể hủy ngang | Dòng đầu trùng tên parent; dòng `Trong đó` là non-additive và chưa có leaf riêng. |

- **Lượt hiện hành trước:** E-0098 giữ riêng ACB p26, MBB p51, VPB p68,
  CTG p48 và VIB p50 với 47 mapping/92 ô/34 phương trình; HDB/VCB/BID là
  bounded absence và VPB là nguồn Q1/2026. Các gap CL-001–CL-014 cùng nghĩa
  được giữ một lần trong ledger, không bị annual result relabel.

Kết quả annual-2025:
`docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json`.

## 48. Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý

- **Annual-2025 đã map/xác minh:** VPB p94 và VCB p73–74. Đã map 41 khoản
  mục/35 ô số và kiểm tra 9 phương trình. Hai trang bảng landscape được giữ
  theo chiều đọc chuẩn và cùng một hệ tọa độ canonical; graph nhận ra nhánh
  giá trị ghi sổ, nhánh giá trị hợp lý, tài sản, nợ phải trả và tiếp trang mà
  không dùng bank/page để route.
- **Annual-2025 không có bảng chi tiết trong báo cáo:** ACB, MBB, HDB, CTG,
  BID và VIB. ACB chỉ công bố diễn giải rằng chưa xác định giá trị hợp lý;
  các bảng phái sinh, tín dụng và rủi ro của năm bank còn lại là đối chứng
  gần nhưng không phải bảng đồng thời có giá trị ghi sổ và giá trị hợp lý.
- **Annual-2025 còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 94 | Giá trị hợp lý của phần lớn tài sản/nợ tài chính ký hiệu `(*)` | PDF ghi chưa xác định được giá trị hợp lý; không đổi `(*)` thành 0 và không sao chép giá trị ghi sổ. |
| VCB | 74 | Giá trị hợp lý của phần lớn tài sản/nợ tài chính ký hiệu `(*)` | Nguồn ghi không thể ước tính đáng tin cậy và không công bố giá trị số; giữ OPEN. |

- **Lượt hiện hành trước:** E-0099 giữ riêng VPB p86, VCB p44–45 và CTG
  p51 với 64 mapping/55 ô/12 phương trình; ba nhóm `(*)` FI-001–FI-003 vẫn
  OPEN và VPB là nguồn Q1/2026.

Kết quả annual-2025:
`docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json`.

## 49. Rủi ro tiền tệ

### BCTC hợp nhất kiểm toán năm 2025 — E-0155

- **Đã map/xác minh:** ACB p84, MBB p97, VPB p88, HDB p63, VCB p80,
  CTG p71, BID p65 và VIB p71. Một graph chung nhận diện owner rủi ro tiền
  tệ, các trục tiền tệ, năm báo cáo, đơn vị và các dòng tổng/trạng thái mà
  không dùng bank/page để route. Kết quả có 155 mapping/155 ô số, 74 phương
  trình khép đúng và 8 dấu `-` được xác thực trên pixel trước khi đổi thành 0.
- **Không có cụm trong annual-2025:** Không bank nào; cả 8/8 filing có đúng
  một vùng hiện kỳ thỏa đầy đủ. Bốn bảng so sánh tại ACB p85, MBB p98,
  CTG p72 và VIB p72 được nhận diện nhưng loại khỏi mapping hiện kỳ.
- **Có nhưng còn khoản mục chưa map:** bảy trục nguồn dưới đây chưa có nhánh
  tương đương trong schema. Các số nguồn vẫn được giữ trong phương trình và
  không bị gộp ngầm vào `Tiền tệ khác`.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 84 | AUD | Schema 1352–1482 chưa có trục AUD. |
| ACB | 84 | CAD | Schema 1352–1482 chưa có trục CAD. |
| ACB | 84 | JPY | Schema 1352–1482 chưa có trục JPY. |
| ACB | 84 | Vàng | Schema chưa có nhánh trục vàng. |
| VPB | 88 | Vàng | Schema chưa có nhánh trục vàng. |
| HDB | 63 | Vàng | Schema chưa có nhánh trục vàng. |
| CTG | 71 | Vàng | Schema chưa có nhánh trục vàng. |

Gemma 4 local GPU chỉ cứu hộ đúng hai crop nhãn BID `Trạng thái tiền tệ nội
bảng` và `Trạng thái tiền tệ ngoại bảng` mà VietOCR sai dấu/chữ. Thử nghiệm
cả trang có một chữ số sai nên Gemma không có numeric authority; mọi số vẫn
được ràng buộc bởi pixel, trục số nguồn và phương trình kế toán.

Kết quả annual-2025:
`docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json`.

### Lượt hiện hành trước — E-0105

- **Đã map/xác minh:** MBB p58, VPB p80, HDB p38–39, VCB p50–51,
  CTG p60 và VIB p65–66. Sau adjudication E-0105 có 120 mapping/136 ô số và
  51 phương trình khép đúng. Dấu `-` ngoại bảng HDB/VIB được chuẩn hóa 0;
  VCB `Tổng nợ phải trả — VND` map vào 1418 theo phạm vi tiêu đề bảng; hai
  residual đúng 1 đơn vị của VPB được giữ nguyên số nguồn và ghi là sai số
  trình bày/làm tròn, không sửa chữ số.
- **Không có bảng rủi ro tiền tệ chi tiết trong báo cáo:** ACB và BID. Toàn PDF
  đã được quét; các vùng rủi ro lãi suất, thanh khoản và giá trị hợp lý được
  giữ làm đối chứng âm, không relabel thành rủi ro tiền tệ.
- **Còn thiếu:** chỉ còn ba nhánh vàng vì schema 1352 chưa có currency-axis
  vàng; 11 ô nguồn vẫn được giữ nguyên, không gộp vào `Tiền tệ khác`.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 80 | Trục vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Schema 1352 hiện chưa có nhánh trục vàng. |
| HDB | 39 | Trục vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Schema chưa có nhánh trục vàng. |
| CTG | 60 | Trục vàng — tổng tài sản, trạng thái nội bảng/kết hợp | Ô tổng nợ và ngoại bảng vàng để trống; schema cũng chưa có nhánh vàng. |

## 50. Rủi ro lãi suất

### BCTC hợp nhất kiểm toán năm 2025 — E-0156

- **Đã map/xác minh:** ACB p87, MBB p95, VPB p85, HDB p65, VCB p78,
  CTG p75, BID p67 và VIB p68. Full-PDF scan tìm đúng một vùng ở cả 8/8
  filing. Cùng một graph owner/trục/dòng lõi xử lý bảng thường, bảng landscape,
  header nhiều dòng và header CTG gộp text `Quá hạn`/`Không chịu lãi` nhưng
  vẫn giữ hai cột số độc lập. Kết quả xác minh 280 mapping/280 ô số, 87
  phương trình exact và 10 dấu `-` được xác thực trên pixel trước khi đổi
  thành 0.
- **Không có cụm trong annual-2025:** Không bank nào. Bốn bảng so sánh ACB
  p88, MBB p96, CTG p76 và VIB p69 được nhận diện nhưng không dùng thay kỳ
  hiện tại. HDB p65 là một bảng continuation duy nhất không in lại ngày; kỳ
  hiện tại được kế thừa từ period receipt toàn tài liệu, còn ngày 31/12/2014
  của Thông tư NHNN bị loại.
- **Có nhưng còn khoản mục chưa map:** chỉ còn tổng VPB p85. Năm số nguồn
  được giữ nguyên; `198.106.343 + 2 = 198.106.345`, trong khi trạng thái kết
  hợp in `198.106.343`, residual 2. Không sửa số hoặc tự coi là làm tròn khi
  chưa có adjudication riêng.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 85 | Tổng cộng — tổng tài sản, tổng nợ, trạng thái nội bảng, ngoại bảng và kết hợp | Trạng thái nội bảng + ngoại bảng lệch 2 so với trạng thái kết hợp in; giữ 5 ô source-bound và OPEN. |

Kết quả annual-2025:
`docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-verified-mapping-v1.json`.

### Lượt hiện hành trước — E-0105

- **Đã map/xác minh:** MBB p57, VPB p78, HDB p41, VCB p49, CTG p55 và
  VIB p62–63. E-0105 đóng toàn bộ 26 gap trước đây: dấu `-` được đọc là 0,
  các dòng nội/ngoại/kết hợp được tách đúng theo tọa độ, và bảng xoay VIB
  được Gemma 4 đọc độc lập trên pixel rồi kiểm tra lại bằng 36 phương trình.
  Toàn family hiện có 234 mapping/279 ô số và 108 phương trình khép đúng.
- **Không có bảng rủi ro lãi suất chi tiết trong báo cáo:** ACB và BID.
  Toàn PDF đã được quét; các đoạn thuyết minh chính sách không có
  bảng tài sản/nợ/trạng thái theo trục định giá lại nên không bị
  relabel thành bảng chi tiết.
- **Còn thiếu:** Không còn khoản mục nguồn chờ map trong family này.

## 51. Rủi ro thanh khoản

- **Đã map/xác minh:** MBB p60, HDB p43, VCB p53, CTG p58 và VIB p68–69;
  VPB p82 đã map các trục khép số. E-0105 đóng các dấu `-` tổng nợ quá hạn
  thành 0 và đọc lại đủ bảng xoay VIB bằng Gemma 4 + pixel + 16 phương trình.
  Toàn family hiện có 129 mapping/153 ô số và 51 phương trình khép đúng.
- **Không có bảng rủi ro thanh khoản chi tiết trong báo cáo:** ACB và BID.
  Toàn PDF đã được quét; diễn giải chính sách hoặc bảng rủi ro lãi suất/tiền
  tệ không bị relabel thành bảng thanh khoản.
- **Còn thiếu:** chỉ còn bốn trục VPB p82 có residual lớn, không phải sai số
  làm tròn và chưa được tự sửa:

| Bank | Trang | Trục nguồn | Kiểm tra chưa khép |
| --- | ---: | --- | --- |
| VPB | 82 | Từ trên 1 đến 3 tháng | `124.257.654 - 154.128.528 = (29.870.874)`, nguồn in `(29.876.874)`; lệch 6.000. |
| VPB | 82 | Từ trên 1 đến 5 năm | `359.512.349 - 179.337.661 = 180.174.688`, nguồn in `180.450.188`; lệch 275.500. |
| VPB | 82 | Từ trên 3 đến 12 tháng | `290.157.812 - 461.620.500 = (171.462.688)`, nguồn in `(171.456.687)`; lệch 6.001. |
| VPB | 82 | Đến 1 tháng | `392.844.039 - 389.919.465 = 2.924.574`, nguồn in `2.649.075`; lệch 275.499. |

## 52. Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo

- **Đã map/xác minh:** MBB p61 map đủ 10 đồng tiền có trong schema; VPB p90
  map 10 đồng tiền; CTG p61 map 10 đồng tiền; BID p35 map 8 đồng tiền; VIB
  p71 map 8 đồng tiền. Tổng cộng 46 mapping/92 ô tỷ giá hiện kỳ và so sánh
  được đối chiếu trực tiếp với pixel và trục số nguồn. BID dùng chính sách
  quy đổi ngoại tệ sang VND nhìn thấy tại p13; VPB giữ đúng nguồn Q1/2026.
- **Không có bảng tỷ giá chi tiết trong báo cáo:** ACB, HDB và VCB. Toàn PDF
  đã được quét; bảng rủi ro tiền tệ, lãi suất, thanh khoản và diễn giải chính
  sách không bị relabel thành bảng tỷ giá cuối kỳ.
- **Có nhưng còn thiếu:** 15 dòng tiền tệ/vàng nhìn thấy và đã xác minh số,
  nhưng schema 5935–5945 chưa có leaf tương ứng nên giữ `OPEN`.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 90 | CNY | Chưa có leaf CNY dưới family 5935. |
| VPB | 90 | DKK | Chưa có leaf DKK dưới family 5935. |
| VPB | 90 | NZD | Chưa có leaf NZD dưới family 5935. |
| VPB | 90 | Vàng (XAU) | Chưa có leaf vàng/XAU dưới family 5935. |
| CTG | 61 | NZD | Chưa có leaf NZD dưới family 5935. |
| CTG | 61 | NOK | Chưa có leaf NOK dưới family 5935. |
| CTG | 61 | DKK | Chưa có leaf DKK dưới family 5935. |
| CTG | 61 | HKD | Chưa có leaf HKD dưới family 5935. |
| CTG | 61 | CNY | Chưa có leaf CNY dưới family 5935. |
| CTG | 61 | KRW | Chưa có leaf KRW dưới family 5935. |
| CTG | 61 | LAK | Chưa có leaf LAK dưới family 5935. |
| VIB | 71 | DKK | Chưa có leaf DKK dưới family 5935. |
| VIB | 71 | HKD | Chưa có leaf HKD dưới family 5935. |
| VIB | 71 | NOK | Chưa có leaf NOK dưới family 5935. |
| VIB | 71 | XAU | Chưa có leaf vàng/XAU dưới family 5935. |

## Bảng tổng hợp

Ký hiệu: **✓** đã map/xác minh; **—** không có vùng family tương ứng; **△** đã
thấy vùng nguồn nhưng chưa map; **✓\*** đã map phần mục tiêu, còn hàng ngoài lõi
hoặc group parent chỉ giữ để kiểm tra.

| Cụm | ACB | MBB | VPB | HDB | VCB | CTG | BID | VIB | Còn chưa map |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tiền, kim loại quý, đá quý | ✓ p45 | ✓ p46 | ✓ p41 | ✓ p33 | ✓ p35 | ✓ p39 | ✓ p39 | ✓ p35 | 0 dòng trong 8 BCTC hợp nhất kiểm toán annual-2025 |
| Tiền gửi tại NHNN | ✓ p45 | ✓ p46 | ✓ p41 | ✓ p33 | ✓ p35 | ✓ p39 | ✓ p39 | ✓ p35 | 0 dòng trong 8 BCTC hợp nhất kiểm toán annual-2025; Lào/Campuchia → 574 |
| Tiền gửi/vay TCTD khác | ✓ p46 | ✓ p48 | ✓ p42 | ✓ p34 | ✓ p36 | ✓ p40 | ✓ p39 | ✓ p36 | 0 dòng trong 8 BCTC hợp nhất kiểm toán annual-2025 |
| Chứng khoán kinh doanh | ✓ p47 | ✓ p49 | ✓ p43 | ✓ p34 | ✓ p37 | ✓ p41 | ✓ p40 | — | 0 dòng trong 8 BCTC hợp nhất kiểm toán annual-2025; VIB chỉ có family đầu tư |
| Công cụ tài chính phái sinh | ✓ p49 | ✓ p66 | ✓ p44 | ✓ p35 | — | ✓ p42 | ✓ p41 | ✓ p37 | 0 dòng trong 8 BCTC hợp nhất kiểm toán annual-2025; VCB không có family |
| Loại hình cho vay | ✓ p17 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p30 | ✓ p38 | ✓ p22 | ✓ p33 | 0 |
| Ngành nghề kinh doanh | ✓ p51 | ✓ p52 | ✓ p47 | ✓ p37 | ✓ p40 | — | ✓ p42 | ✓ p38 | 0 dòng; VCB gộp `Thương mại, dịch vụ` → 6073; CTG không có family trong filing annual-2025 |
| Chất lượng cho vay | ✓ p50 | ✓ p51 | ✓ p45 | ✓ p36 | ✓ p39 | ✓ p43 | ✓ p42 | ✓ p66 | 0 dòng trong 8 BCTC hợp nhất kiểm toán annual-2025; 1944 tách riêng tại ACB/MBB/VPB |
| Dư nợ theo thời gian | ✓ p50 | ✓ p51 | ✓ p45 | ✓ p36 | ✓ p40 | ✓ p44 | ✓ p42 | ✓ p38 | 0 dòng annual-2025; MBB/VPB map margin, HDB giữ dân số bổ sung source-only |
| Cho vay theo loại tiền tệ | ✓ p51 | — p51–52 | — p45–47 | ✓ p37 | — p39–40 | — p43–44 | — p41–42 | — p37–39 | 0 dòng annual-2025; HDB giữ dân số thư tín dụng bổ sung source-only |
| Cho vay theo khu vực địa lý | ✓ p77 | ✓ p91 | — p81 | — p60 | — | — | — p63 | ✓ p59–60 | 0 dòng annual-2025; ba bảng địa lý rộng hơn không bị thu hẹp ngầm |
| Doanh nghiệp/đối tượng KH | — | ✓ p52 | ✓ p46 | ✓ p36 | ✓ p40 | — | ✓ p42 | ✓ p39 | 0 dòng; VCB gộp `Hợp tác xã và công ty tư nhân` → 6074 |
| Dự phòng cho vay | ✓ p51 | ✓ p53 | ✓ p48 | ✓ p38 | ✓ p41 | ✓ p44 | ✓ p43 | ✓ p39 | 0 dòng annual-2025; 18 lane/79 dòng/18 phương trình; 9 DASH→0 |
| Hoạt động mua nợ | — | ✓ p54 | ✓ p49 | ✓ p39 | — | — | — | ✓ p40 | 0 dòng annual-2025; 15 mapping/30 ô/19 phương trình; HDB không in dòng lãi |
| Tiền gửi khách hàng | ✓ p62 | ✓ p65 | ✓ p60–61 | ✓ p45 | ✓ p53 | ✓ p52 | ✓\* p51 | ✓ p46–47 | Annual-2025: 2 dòng BID gộp còn OPEN; 159 mapping/43 phương trình. Lượt hiện hành trước: 0 dòng OPEN |
| Chứng khoán đầu tư | ✓ p52–53 | ✓ p54–56 | ✓ p50–52 | ✓ p39–40 | ✓ p42–43 | ✓ p45–46 | ✓ p44–45 | ✓ p40–41 | 0 dòng; MBB gộp → 807, HDB cộng hai thành phần → 831 |
| Đầu tư dài hạn khác | ✓ p54 | ✓ p57 | ✓ p52 | ✓ p41 | ✓ p44–45 | ✓ p47 | ✓ p45 | ✓ p41 | 0 dòng annual-2025; 28 mapping/56 ô/11 phương trình |
| Tăng, giảm TSCĐ hữu hình | ✓ p55 | ✓ p58 | ✓ p53 | ✓ p41 | ✓ p48 | ✓ p48 | ✓ p47 | ✓ p42 | 0 dòng annual-2025; 105 mapping/32 phương trình; CTG/BID/VIB dùng numeric challenger trên ảnh xoay |
| Tăng, giảm TSCĐ thuê tài chính | — p55→56 | — p58→60 | — p53→54 | — p41→42 | — p48→49 | — p48→49 | — p47→48 | — p42→43 | 0 dòng annual-2025; cả 8 PDF xác nhận không có bảng chi tiết |
| Tăng, giảm TSCĐ vô hình | ✓ p56 | ✓ p60 | ✓ p54 | ✓ p42 | ✓ p49 | ✓ p49 | ✓ p48 | ✓ p43 | 0 dòng annual-2025; 107 mapping/32 phương trình; kết quả hiện hành cũ vẫn byte-exact |
| Tăng, giảm bất động sản đầu tư | ✓ p57 | ✓ p61 | — p54→55 | — p42 | — p49→50 | — p49→50 | — p48→49 | — p43→44 | 0 dòng annual-2025; 18 mapping/27 phương trình; ACB cộng có kiểm soát hai bảng anh em |
| Tài sản Có khác | ✓\* p58–60 | ✓\* p62–63 | ✓\* p55–57 | ✓\* p42–44 | ✓\* p50–52 | ✓\* p50–51 | ✓\* p49–50 | ✓\* p44–45 | Annual-2025: 35 dòng OPEN, 134 mapping/66 phương trình; lượt hiện hành trước: 12 dòng OPEN |
| Các khoản nợ Chính phủ/NHNN | ✓ p60 | ✓ p63 | ✓ p58 | ✓ p44 | ✓ p52 | ✓ p51 | ✓ p50 | ✓ p45 | Annual-2025: 0 dòng OPEN, 47 mapping/46 phương trình; sáu DASH→0 và ô HDB `1` đều pixel-bound |
| Vốn nhận tài trợ/ủy thác đầu tư | ✓ p63 | ✓ p66 | ✓ p62 | ✓ p45 | ✓ p53 | ✓ p53 | ✓ p51 | ✓ p47 | 0 dòng annual-2025; 20 mapping/8 phương trình; VCB DASH→0. Lượt hiện hành trước giữ riêng 6 mapping tại MBB/VPB/VIB |
| Phát hành giấy tờ có giá | ✓ p63 | ✓ p66 | ✓\* p62 | ✓\* p46 | ✓\* p54 | ✓ p53–54 | ✓ p52 | ✓ p47 | Annual-2025: 5 dòng OPEN, 70 mapping/34 phương trình, 11 DASH→0; lượt hiện hành trước còn 3 dòng VPB OPEN |
| Các khoản phải trả và công nợ khác | ✓ p64 | ✓ p67 | ✓ p63 | ✓ p47 | ✓ p54 | ✓ p54 | ✓ p52 | ✓ p48 | Annual-2025: 0 dòng OPEN, 53 mapping/32 phương trình, 3 DASH→0; E-0132A đóng 18 dòng lượt hiện hành vào 1127 `Khác` |
| Vốn và các quỹ | ✓ p65–66 | ✓ p69–70 | ✓\* p66–67 | ✓\* p48–49 | ✓\* p56–57 | ✓\* p55–56 | ✓\* p53–54 | ✓\* p49–50 | Annual-2025: 7 mục OPEN do thiếu leaf số dư vốn; 74 mapping/132 ô/18 phương trình; 3 bảng xoay đã full-page re-detect. Lượt hiện hành trước: 10 OPEN/65 mapping |
| Thu nhập lãi và các khoản thu nhập tương tự | ✓ p67 | ✓ p72 | ✓ p68 | ✓ p49 | ✓ p57 | ✓ p57 | ✓ p54 | ✓ p50 | Annual-2025: 0 dòng OPEN, 55 mapping/110 ô/28 phương trình; MBB gộp → 6075, HDB phí L/C → 6076. Lượt hiện hành E-0079 giữ riêng 54 mapping |
| Chi phí lãi và các khoản tương tự chi phí lãi | ✓ p67 | ✓ p72 | ✓ p68 | ✓ p49 | ✓ p58 | ✓ p57 | ✓ p55 | ✓ p50 | Annual-2025: 0 dòng OPEN, 40 mapping/80 ô/16 phương trình. Lượt hiện hành E-0081 giữ riêng 40 mapping; VPB của lượt đó là nguồn Q1 |
| Thu nhập từ lãi thuần | ✓ p10 | ✓ p13 | ✓ p12 | ✓ p10 | ✓ p11 | ✓ p11 | ✓ p12 | ✓ p11 | Annual-2025: 0 dòng OPEN, 8 mapping/16 ô/48 đối chiếu statement–TM–công thức |
| Thu nhập/chi phí/lãi thuần hoạt động dịch vụ | ✓ p67 | ✓ p72 | ✓ p69 | ✓ p50 | ✓ p58 | ✓\* p58 | ✓ p55 | ✓ p50 | Annual-2025: 2 hàng CTG OPEN, 101 mapping/202 ô/48 phương trình. Lượt hiện hành trước: 43 mapping tại MBB/VPB/VIB; VPB là Q1 |
| Lãi/lỗ thuần kinh doanh vàng và ngoại hối | ✓ p68 | ✓ p73 | ✓ p69 | ✓ p50 | ✓ p59 | ✓ p58 | ✓ p55 | ✓ p51 | Annual-2025: 0 dòng OPEN, 69 mapping/138 ô logic/152 thành phần, 48 phương trình, 5 DASH→0. Lượt hiện hành trước: 23 mapping tại MBB/VPB/VIB; VPB là Q1 |
| Lãi/lỗ thuần mua bán chứng khoán kinh doanh | ✓ p68 | ✓ p73 | ✓ p70 | ✓ p50 | ✓ p59 | ✓ p58 | ✓ p56 | — | Annual-2025: 0 dòng OPEN, 27 mapping/54 ô/14 phương trình; HDB không in dự phòng; VIB chỉ có family đầu tư. Lượt hiện hành trước: 28 mapping, VPB là Q1 |
| Lãi/lỗ thuần mua bán chứng khoán đầu tư | ✓ p68 | ✓ p73 | ✓ p70 | ✓ p50 | ✓ p59 | ✓ p59 | ✓ p56 | ✓ p51 | Annual-2025: 0 dòng OPEN, 32 mapping/64 ô logic từ 70 thành phần/16 phương trình, 5 DASH→0. Lượt hiện hành trước: 28 mapping; VCB bounded absence, VPB là Q1 |
| Lãi thuần CK kinh doanh + CK đầu tư | — | — | — | — | — | — | — | — | Annual-2025: 8 bounded absences, BID p56 là tiêu đề đối chứng âm, 0 dòng OPEN. Lượt hiện hành trước: MBB p47 có 1 mapping/2 ô/2 phương trình |
| Thu nhập góp vốn/mua cổ phần/cổ tức | ✓ p69 | ✓ p74 | ✓ p71 | ✓ p51 | ✓ p60 | ✓\* p59 | ✓ p56 | — | Annual-2025: 1 dòng CTG OPEN, 28 mapping/56 ô/20 phương trình, 4 DASH→0; VIB không có note chi tiết. Lượt hiện hành trước: 27 mapping; VPB là Q1 |
| Chi phí quản lý chung/Chi phí hoạt động | ✓\* p70 | ✓\* p74 | ✓\* p72 | ✓\* p51 | ✓ p61 | ✓\* p60 | ✓ p57 | ✓ p52 | Annual-2025: 14 dòng OPEN, 103 mapping/206 ô/42 phương trình, 4 lỗi số VietOCR bị nguồn/pixel/accounting bác bỏ. Lượt hiện hành trước: 4 OPEN/99 mapping; VPB là Q1 |
| Chi phí dự phòng rủi ro tín dụng | ✓ p70 | ✓ p75 | ✓ p73 | — | ✓ p61 | — | — | ✓ p52 | Annual-2025: 0 dòng OPEN, 25 mapping/50 ô/12 phương trình, 1 DASH→0; HDB/CTG/BID không có note chi tiết. Lượt hiện hành trước: 15 mapping, E-0100 đóng CRPE-001/002 → 1228; VPB là Q1 |
| Thu nhập/chi phí/lãi thuần hoạt động khác | ✓ p69 | ✓ p74 | ✓ p71 | ✓ p51 | ✓ p60 | ✓ p59 | ✓ p56 | ✓ p51 | Annual-2025: 0 dòng OPEN, 72 mapping/144 ô/48 phương trình, 8/8 vùng unique. Lượt hiện hành trước: 23 mapping; OACT-001 → 1239; VPB là Q1 |
| Chi phí thuế thu nhập doanh nghiệp | ✓\* p71 | ✓\* p76 | ✓\* p64 | ✓ p52 | ✓ p62 | ✓\* p60 | ✓ p57 | ✓\* p53 | Annual-2025: 7 dòng OPEN; 61 mapping/120 ô/32 phương trình; 2 lỗi số VietOCR bị source challenger bác bỏ; 0 family absence |
| Tiền và các khoản tương đương tiền | ✓ p73 | ✓ p78 | ✓ p73 | ✓ p54 | ✓ p64 | ✓ p62 | ✓ p58 | ✓ p50 | Annual-2025: 0 dòng OPEN, 43 mapping/86 ô/18 phương trình, 3 DASH→0; lượt hiện hành trước giữ riêng 31 mapping và HDB/BID absence |
| Mua mới và thanh lý các công ty con | — | — | — | — | — | — | — | — | Annual-2025: 8 bounded absences/695 trang/25 đối chứng âm, 0 OPEN; lượt hiện hành E-0093 giữ nguyên 8 absences |
| Thu nhập nhân viên | ✓ p73 | — | ✓ p73 | — | — | — | ✓ p58 | ✓ p54 | Annual-2025: 0 dòng OPEN, 18 mapping/36 ô/16 phương trình; ACB bình quân năm được kiểm tra rồi quy đổi 12 tháng. Lượt hiện hành trước giữ riêng 13 mapping; VPB là nguồn Q1 |
| Nghĩa vụ với ngân sách nhà nước | ✓ p73 | ✓ p68 | ✓ p64 | ✓ p47 | ✓ p65 | ✓ p62 | ✓ p52 | ✓ p52 | Annual-2025: 0 dòng OPEN, 35 mapping/140 ô logic/35 phương trình, 1 DASH→0; CTG net nhánh phải thu/phải trả bằng tổng có dấu. Lượt hiện hành trước giữ riêng 33 mapping; VCB absence, VPB Q1 |
| Tài sản thế chấp của khách hàng | ✓ p74 | — | ✓ p74 | ✓ p54 | — | — | — | ✓ p54 | Annual-2025: 0 dòng OPEN, 25 mapping/50 ô/10 phương trình; MBB/VCB/CTG/BID bounded absence. Lượt hiện hành trước giữ riêng VPB p67, VCB p47, VIB p49 |
| Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | ✓ p74 | ✓ p78 | ✓ p74 | — | — | ✓ p63 | — | ✓ p54 | Annual-2025: 0 dòng OPEN, 13 mapping/26 ô/10 phương trình; HDB/VCB/BID bounded absence. Lượt hiện hành trước giữ riêng 3 dòng OPEN tại VPB/VIB |
| Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra | ✓\* p75 | ✓ p79 | ✓\* p75 | ✓ p55 | — | ✓ p63 | ✓ p59 | ✓ p55 | Annual-2025: 13 dòng OPEN tại ACB/VPB, 58 mapping/114 ô/46 phương trình; VCB bounded absence. Lượt hiện hành trước giữ riêng 47 mapping; VPB của lượt đó là Q1 |
| Công cụ tài chính — giá trị ghi sổ/hợp lý | — | — | ✓\* p94 | — | ✓\* p73–74 | — | — | — | Annual-2025: 2 nhóm giá trị hợp lý OPEN; 41 mapping, 35 ô số, 9 phương trình; 6 bank không có bảng chi tiết. Lượt hiện hành E-0099 giữ riêng 64 mapping tại VPB/VCB/CTG; VPB là Q1 |
| Rủi ro tiền tệ | ✓\* p84 | ✓ p97 | ✓\* p88 | ✓\* p63 | ✓ p80 | ✓\* p71 | ✓ p65 | ✓ p71 | Annual-2025: 7 trục/34 ô OPEN ngoài schema, 155 mapping/155 ô số/74 phương trình; 8/8 vùng unique. Lượt hiện hành trước giữ riêng 120 mapping và 3 nhánh vàng OPEN; VPB của lượt đó là Q1 |
| Rủi ro lãi suất | ✓\* p87 | ✓\* p95 | ✓\* p85 | ✓\* p65 | ✓\* p78 | ✓\* p75 | ✓\* p67 | ✓\* p68 | Annual-2025: 1 nhóm/5 ô VPB OPEN vì residual 2; 280 mapping/280 ô/87 phương trình, 8/8 vùng unique. Lượt hiện hành trước giữ riêng 234 mapping/279 ô/108 phương trình và OPEN=0; VPB của lượt đó là Q1 |
| Rủi ro thanh khoản | — | ✓ p60 | ✓\* p82 | ✓ p43 | ✓ p53 | ✓ p58 | — | ✓ p68–69 | 4 trục/12 ô VPB OPEN vì residual lớn; 129 mapping, 153 ô số, 51 phương trình; VPB là nguồn Q1 |
| Tỷ giá ngoại tệ cuối kỳ | — | ✓ p61 | ✓\* p90 | — | — | ✓\* p61 | ✓ p35 | ✓\* p71 | 15 dòng OPEN; 46 mapping/92 ô; VPB là nguồn Q1, BID dùng policy VND p13 |
