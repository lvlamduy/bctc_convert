# Family 15 — Phân loại tiền gửi của khách hàng

Checkpoint này là kết quả audit trên tập bất biến **271 PDF / 14.945 trang** của
19 ngân hàng mới, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Tập chính không có
8 ngân hàng cũ, không có PDF năm 2024 và không gọi lại provider.

## Kết quả cuối

| Trạng thái | PDF |
|---|---:|
| READY | 264 |
| NOT_OBSERVED | 0 |
| UNRESOLVED | 7 |
| **Tổng** | **271** |

- Kiểm tra chéo: **264 + 0 + 7 = 271 PDF**; có **3.898 mapping**.
- Family xuất hiện trong toàn bộ 271 PDF. Vì vậy 13 kết quả `NOT_OBSERVED` ở
  checkpoint full-271 đầu của đợt audit đã được rà lại và không còn false
  negative.
- Có **23 PDF READY còn 31 dòng SOURCE_ONLY/chưa có mapping chính xác**. Các
  dòng này được liệt kê đầy đủ ở phần ledger bên dưới; chúng không bị tính là
  lỗi của toàn bộ PDF.
- Có **7 PDF UNRESOLVED thật sự**, đều có khoản mục gộp không thể phân bổ an
  toàn hoặc có mâu thuẫn ngay trong hàng nguồn. Không có trường hợp nào bị giữ
  UNRESOLVED chỉ vì alias, header, đơn vị, bảng tách trang hoặc continuation.

## Tiến độ theo ngân hàng

| Ngân hàng | PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED | Mapping |
|---|---:|---:|---:|---:|---:|
| ABB | 12 | 12 | 0 | 0 | 132 |
| BAB | 10 | 10 | 0 | 0 | 144 |
| BVB | 14 | 14 | 0 | 0 | 364 |
| EIB | 16 | 16 | 0 | 0 | 172 |
| KLB | 16 | 16 | 0 | 0 | 257 |
| LPB | 7 | 7 | 0 | 0 | 175 |
| MSB | 16 | 16 | 0 | 0 | 218 |
| NAB | 16 | 14 | 0 | 2 | 152 |
| NVB | 16 | 16 | 0 | 0 | 156 |
| OCB | 16 | 16 | 0 | 0 | 174 |
| PGB | 7 | 7 | 0 | 0 | 78 |
| SGB | 14 | 14 | 0 | 0 | 224 |
| SHB | 16 | 16 | 0 | 0 | 198 |
| SSB | 16 | 16 | 0 | 0 | 288 |
| STB | 16 | 16 | 0 | 0 | 236 |
| TCB | 16 | 12 | 0 | 4 | 108 |
| TPB | 16 | 16 | 0 | 0 | 304 |
| VAB | 15 | 14 | 0 | 1 | 190 |
| VBB | 16 | 16 | 0 | 0 | 328 |
| **Tổng** | **271** | **264** | **0** | **7** | **3.898** |

## Cấu trúc schema và cấu trúc PDF đã nhận diện

ReportNormId 1055 `Tiền gửi của khách hàng` là context family. Hai nhánh chính
là 1056 `Theo tiền tệ và loại tiền gửi` và 1075 `Theo loại hình doanh nghiệp`;
các parent này dùng để khóa cấu trúc, không tạo mapping trùng với các leaf.

| Nhóm | ReportNormId được dùng |
|---|---|
| Không kỳ hạn | 1057–1059 |
| Có kỳ hạn | 1060–1062 |
| Tiền gửi tiết kiệm | 1063–1065 |
| Tiền ký quỹ | 1066–1068 |
| Tiền gửi vốn chuyên dùng | 1069–1071 |
| Tiền gửi đảm bảo thanh toán khác | 1072–1074 |
| Tiền gửi của tổ chức kinh tế và chi tiết loại hình | 5977, 1076–1091 |

Trong 264 PDF READY, có 250 bảng dạng hàng khoản mục × hai cột kỳ và 14 bảng
tách tiếp nối qua các trang liền kề. Có 244 PDF dùng triệu đồng và 20 PDF dùng
đồng Việt Nam; engine giữ đúng đơn vị nguồn, không tự nhân/chia. Phần phân loại
khách hàng có 145 PDF khép đầy đủ, 115 PDF không công bố subtable này và 4 PDF
NVB có các dòng biết chắc vẫn được map, còn ba dòng gộp được giữ SOURCE_ONLY.

Các biến thể đã xử lý bằng rule chung, không route theo tên ngân hàng/file/trang:

- bảng bị tách trang, header kỳ ở fragment trước và unit nằm ở owner row hoặc
  trang báo cáo chính liền trước;
- header dạng ngày cụ thể hoặc vai trò kỳ như `Cuối kỳ`, `Đầu kỳ`,
  `Số dư cuối quý`; reject nếu hai kỳ, đơn vị hoặc quần thể không tương thích;
- `Tiền gửi tiết kiệm không kỳ hạn` và `Tiền gửi tiết kiệm có kỳ hạn` được cộng
  đúng các dòng nhìn thấy để map aggregate 1063; không tự phân bổ child nếu PDF
  không công bố theo tiền tệ;
- `Tiền gửi ký quỹ` tương đương 1066, cùng các child VND/ngoại tệ 1067–1068;
- `Tiền gửi đảm bảo thanh toán khác` của STB map 1072–1074;
- `Công ty liên doanh, hợp doanh` map 1086 và `Công ty hợp danh` map 1087, không
  còn gộp nhầm hai bản chất;
- ô nguồn trống luôn được giữ là không quan sát, không bao giờ đổi thành số 0
  từ phương trình. Role có cả hai kỳ trống bị loại khỏi mapping/phương trình;
  role chỉ trống một kỳ vẫn giữ kỳ nhìn thấy và mang state
  `BLANK_SOURCE_CELL` ở kỳ còn lại. Sai số làm tròn chỉ được phép trong đơn vị
  triệu đồng và có bound trên những lane đã quan sát.

### Sáu ô dấu gạch PDF được phục hồi có xác thực

Gemini JSON để `null` ở sáu ô RNID 1069 của VAB, trong khi PDF in rõ dấu gạch
kế toán. Sáu ô này không được backsolve: mỗi repair gắn chính xác SHA/size của
PDF, trang vật lý, SHA ảnh toàn trang render 300 dpi, bbox và SHA RGB của crop,
page-JSON version, section/table/row/column, before-image `null` và after-image
`"-"`. Runner render lại PDF và xác thực toàn bộ receipt trước khi evaluation;
overlay là bản clone nên page JSON nguồn không bị sửa.

| Ordinal | PDF / trang vật lý | Ô được phục hồi |
|---:|---|---|
| 243 | VAB Q1/2025 riêng lẻ, trang 37 | hàng 7, cột kỳ so sánh |
| 246 | VAB Q3/2025 công ty mẹ, trang 38 | hàng 7, cột kỳ so sánh |
| 248 | VAB Q2/2025 hợp nhất, trang 36 | hàng 7, cột kỳ so sánh |
| 249 | VAB năm 2025 hợp nhất kiểm toán, trang 38 | hàng 7, cả hai cột kỳ |
| 252 | VAB Q2/2025 riêng lẻ, trang 36 | hàng 7, cột kỳ so sánh |

Artifact đăng ký
`data/registered/gemini_json_customer_deposit_source_repairs_v1.json` có
SHA-256 `68374357882c15507d77fae8ed69fb9218e6ea827e0af3205ba73bb7e0f6ffa6`,
9.451 byte; repair-axis SHA-256
`4e40b2ebfba53aca39f91635fadc3dc4eb7afd61e141390a68c8e801d58c1980`.
Global source-observation contract quét lại toàn mapping và fail nếu có số bắt
nguồn từ blank hoặc role mapping mà mọi lane đều không quan sát.

## Bảy PDF phải giữ UNRESOLVED

**Family của mọi dòng trong hai ledger dưới đây:** Phân loại tiền gửi của khách
hàng. Mỗi dòng đều dùng số trang vật lý của PDF.

### NAB — một giá trị gộp hai leaf schema

| Ngân hàng | Kỳ / báo cáo | File PDF | Trang | Khoản mục thực tế | Khoản mục cha | Schema gần nhất | Kết luận |
|---|---|---|---:|---|---|---|---|
| NAB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NAB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 54 | `Hợp tác xã và liên hiệp hợp tác xã, hộ kinh doanh` (132.755 / 34.914 triệu đồng) | Tiền gửi của tổ chức kinh tế | 1085 `Hợp tác xã và liên hợp tác xã`; 1089 `Hộ kinh doanh, cá nhân` | **NHIỀU ID CÓ THỂ PHÙ HỢP**: một giá trị nguồn gộp hai leaf; không có căn cứ chia số. |
| NAB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NAB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 55 | `Hợp tác xã và liên hiệp hợp tác xã, hộ kinh doanh` (132.755 / 34.914 triệu đồng) | Tiền gửi của tổ chức kinh tế | 1085 và 1089 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: không được chép cùng một giá trị vào hai ID hoặc tự phân bổ. |

### TCB — một giá trị gộp doanh nghiệp tư nhân và công ty hợp danh

| Ngân hàng | Kỳ / báo cáo | File PDF | Trang | Khoản mục thực tế | Khoản mục cha | Schema gần nhất | Kết luận |
|---|---|---|---:|---|---|---|---|
| TCB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 56 | `Doanh nghiệp tư nhân và công ty hợp danh` (504.162 / 304.209 triệu đồng) | Tiền gửi của các tổ chức kinh tế | 1083 `Doanh nghiệp tư nhân`; 1087 `Công ty hợp danh` | **NHIỀU ID CÓ THỂ PHÙ HỢP**: PDF chỉ in một giá trị chung, không thể tách. |
| TCB | 6 tháng/2025 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf>) | 54 | `Doanh nghiệp tư nhân và công ty hợp danh` (135.235 / 304.209 triệu đồng) | Tiền gửi của các tổ chức kinh tế | 1083 và 1087 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: không đủ dữ liệu phân bổ. |
| TCB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 64 | `Doanh nghiệp tư nhân và công ty hợp danh` (504.162 / 304.209 triệu đồng) | Tiền gửi của các tổ chức kinh tế | 1083 và 1087 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: không đủ dữ liệu phân bổ. |
| TCB | 6 tháng/2025 · Hợp nhất · Soát xét | [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf>) | 58 | `Doanh nghiệp tư nhân và công ty hợp danh` (135.235 / 304.209 triệu đồng) | Tiền gửi của các tổ chức kinh tế | 1083 và 1087 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: không đủ dữ liệu phân bổ. |

### VAB — mâu thuẫn hàng/giá trị ngay trong nguồn trích xuất

| Ngân hàng | Kỳ / báo cáo | File PDF | Trang | Khoản mục thực tế | Khoản mục cha/con liên quan | Schema gần nhất | Kết luận |
|---|---|---|---:|---|---|---|---|
| VAB | Quý 4/2025 · Công ty mẹ · Chưa kiểm toán | [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../../../vietstock_bctc/VAB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf>) | 38 | Sau parent `Tiền gửi có kỳ hạn` để trống xuất hiện một hàng giá trị không có nhãn 92.989.237 / 86.561.698; hàng mang nhãn VND kế tiếp lại có 87.587 / 115.200; hàng ngoại tệ bị in thành `Tiền gửi không kỳ hạn...` và để trống | Parent `Tiền gửi có kỳ hạn`; child VND/ngoại tệ | 1060, 1061, 1062 | **LỖI TRÌNH BÀY NGUỒN / KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ HÀNG**: tổng toàn bảng chỉ khép nếu dịch quan hệ giữa hai giá trị và hai nhãn, nhưng JSON không có geometry đủ thẩm quyền; không tự sửa hay chuyển hàng. |

## SOURCE_ONLY trong PDF READY — 31 dòng

### 1. Mười chín dòng “Công ty TNHH từ hai thành viên trở lên, vốn Nhà nước trên 50%”

Khoản mục này nhìn thấy rõ và thuộc subtable phân loại khách hàng. Schema hiện có
ID 1079 cho **Công ty TNHH một thành viên** vốn Nhà nước trên 50%; vì vậy 1079
khác bản chất. ID 770 có tên gần hơn nhưng nằm dưới nhánh **phân loại cho vay
theo loại hình doanh nghiệp** (parent 766), không thuộc nhánh tiền gửi khách hàng
(parent 1075), nên tuyệt đối không được dùng chéo family.

**Phân loại chung:** `CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT` và `KHOẢN MỤC
MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG`. Các khoản mục khác trong 19 PDF
vẫn map và khép số học nên trạng thái PDF là READY.

| Ngân hàng | Kỳ / báo cáo | File PDF | Trang | Khoản mục cha | Khoản mục thực tế |
|---|---|---|---:|---|---|
| ABB | 6 tháng/2025 · Hợp nhất · Soát xét | [1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf](<../../../../vietstock_bctc/ABB/2025/1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf>) | 55 | Tiền gửi của tổ chức kinh tế | `Công ty TNHH 2 thành viên trở lên có phần vốn góp của nhà nước trên 50%...` |
| ABB | 6 tháng/2025 · Riêng lẻ · Soát xét | [3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf](<../../../../vietstock_bctc/ABB/2025/3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf>) | 53 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| LPB | Quý 4/2025 · Riêng/Ngân hàng · Chưa kiểm toán/không ghi | [BCTC 31.12.2025 VN color.pdf](<../../../../vietstock_bctc/LPB/2025/BCTC 31.12.2025 VN color.pdf>) | 52 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| LPB | Quý 3/2025 · Riêng/Ngân hàng · Chưa kiểm toán/không ghi | [BCTC Q3.2025 VN.pdf](<../../../../vietstock_bctc/LPB/2025/BCTC Q3.2025 VN.pdf>) | 51 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| LPB | Quý 1/2025 · Riêng/Ngân hàng · Chưa kiểm toán/không ghi | [BCTC quý 1 năm 2025.pdf](<../../../../vietstock_bctc/LPB/2025/BCTC quý 1 năm 2025.pdf>) | 50 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| LPB | Quý 2/2025 · Riêng/Ngân hàng · Chưa kiểm toán/không ghi | [BCTC quý 2 năm 2025.pdf](<../../../../vietstock_bctc/LPB/2025/BCTC quý 2 năm 2025.pdf>) | 51 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| LPB | Quý 2/2026 · Riêng/Ngân hàng · Chưa kiểm toán/không ghi | [BCTC quý 2 năm 2026.pdf](<../../../../vietstock_bctc/LPB/2026/BCTC quý 2 năm 2026.pdf>) | 51 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| STB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/STB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 61 | Tiền gửi của tổ chức kinh tế | `Công ty TNHH hai thành viên trở lên có phần vốn góp của Nhà nước trên 50%...` |
| STB | 6 tháng/2025 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/STB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf>) | 60 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| STB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/STB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 62 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| STB | 6 tháng/2025 · Hợp nhất · Soát xét | [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/STB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf>) | 61 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | Quý 1/2025 · Hợp nhất · Chưa kiểm toán | [000000014895152_VI_BaoCaoTaiChinh_HopNhat_Q1_2025.pdf](<../../../../vietstock_bctc/VBB/2025/000000014895152_VI_BaoCaoTaiChinh_HopNhat_Q1_2025.pdf>) | 19 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | Quý 1/2025 · Riêng lẻ · Chưa kiểm toán | [000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf](<../../../../vietstock_bctc/VBB/2025/000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf>) | 20 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | Quý 2/2025 · Riêng lẻ · Chưa kiểm toán | [1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf](<../../../../vietstock_bctc/VBB/2025/1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf>) | 19 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | Quý 2/2025 · Hợp nhất · Chưa kiểm toán | [2_vbb_2025_8_1_afc1d54_vi_baocaotaichinh_hopnhat_q2_2025.pdf](<../../../../vietstock_bctc/VBB/2025/2_vbb_2025_8_1_afc1d54_vi_baocaotaichinh_hopnhat_q2_2025.pdf>) | 18 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | Năm 2025 · Riêng lẻ · Kiểm toán | [2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf](<../../../../vietstock_bctc/VBB/2025/2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf>) | 55 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | 6 tháng/2025 · Riêng lẻ · Soát xét | [3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf](<../../../../vietstock_bctc/VBB/2025/3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf>) | 52 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | 6 tháng/2025 · Hợp nhất · Soát xét | [3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf](<../../../../vietstock_bctc/VBB/2025/3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf>) | 52 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |
| VBB | Năm 2025 · Hợp nhất · Kiểm toán | [3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf](<../../../../vietstock_bctc/VBB/2025/3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf>) | 54 | Tiền gửi của tổ chức kinh tế | Cùng khoản mục trên |

### 2. Mười hai dòng gộp/nhóm riêng của NVB

Bốn PDF NVB vẫn READY vì các dòng biết chắc đã map: 5977, 1076, 1083, 1088,
1089 và toàn bộ nhánh loại tiền gửi tương ứng. Ba dòng dưới đây trong mỗi PDF
không được ép vào một ID gần tên.

| Ngân hàng | Kỳ / báo cáo | File PDF | Trang | Khoản mục thực tế | Schema gần nhất | Lý do chưa map / phân loại |
|---|---|---|---:|---|---|---|
| NVB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 40 | `Công ty CP, TNHH, Hợp danh` | 1082, 1077, 1087; 1084 là `Công ty CP, TNHH, DN tư nhân` | **NHIỀU ID CÓ THỂ PHÙ HỢP / KHÁC BẢN CHẤT**: nguồn gộp hợp danh, còn 1084 gộp doanh nghiệp tư nhân. |
| NVB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 40 | `Công ty chứng khoán, bảo hiểm, tài chính` | Không có leaf cùng quần thể; 1091 `Khác` quá rộng | **KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG**. |
| NVB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 40 | `Kinh tế cá thể, Kinh tế tập thể` | 1089 và 1085 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: một số tiền gộp hai leaf, không thể phân bổ. |
| NVB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 39 | `Công ty CP, TNHH, Hợp danh` | 1082, 1077, 1087; 1084 khác tập hợp | **NHIỀU ID CÓ THỂ PHÙ HỢP / KHÁC BẢN CHẤT**: nguồn gộp hợp danh, còn 1084 gộp doanh nghiệp tư nhân. |
| NVB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 39 | `Công ty chứng khoán, bảo hiểm, tài chính` | Không có leaf cùng quần thể; 1091 `Khác` quá rộng | **KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG**. |
| NVB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 39 | `Kinh tế cá thể, Kinh tế tập thể` | 1089 và 1085 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: một số tiền gộp hai leaf, không thể phân bổ. |
| NVB | 6 tháng/2025 · Hợp nhất · Soát xét | [VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf](<../../../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf>) | 39 | `Công ty CP, TNHH, Hợp danh` | 1082, 1077, 1087; 1084 khác tập hợp | **NHIỀU ID CÓ THỂ PHÙ HỢP / KHÁC BẢN CHẤT**: nguồn gộp hợp danh, còn 1084 gộp doanh nghiệp tư nhân. |
| NVB | 6 tháng/2025 · Hợp nhất · Soát xét | [VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf](<../../../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf>) | 39 | `Công ty chứng khoán, bảo hiểm, tài chính` | Không có leaf cùng quần thể; 1091 `Khác` quá rộng | **KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG**. |
| NVB | 6 tháng/2025 · Hợp nhất · Soát xét | [VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf](<../../../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf>) | 39 | `Kinh tế cá thể, Kinh tế tập thể` | 1089 và 1085 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: một số tiền gộp hai leaf, không thể phân bổ. |
| NVB | 6 tháng/2025 · Riêng lẻ · Soát xét | [VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf](<../../../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf>) | 39 | `Công ty CP, TNHH, Hợp danh` | 1082, 1077, 1087; 1084 khác tập hợp | **NHIỀU ID CÓ THỂ PHÙ HỢP / KHÁC BẢN CHẤT**: nguồn gộp hợp danh, còn 1084 gộp doanh nghiệp tư nhân. |
| NVB | 6 tháng/2025 · Riêng lẻ · Soát xét | [VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf](<../../../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf>) | 39 | `Công ty chứng khoán, bảo hiểm, tài chính` | Không có leaf cùng quần thể; 1091 `Khác` quá rộng | **KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG**. |
| NVB | 6 tháng/2025 · Riêng lẻ · Soát xét | [VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf](<../../../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf>) | 39 | `Kinh tế cá thể, Kinh tế tập thể` | 1089 và 1085 | **NHIỀU ID CÓ THỂ PHÙ HỢP**: một số tiền gộp hai leaf, không thể phân bổ. |

### 3. Hồi quy 8 ngân hàng cũ — 31 dòng cùng schema gap

Phần này **không cộng vào mẫu chính 271 PDF**, nhưng được ghi để ledger cuối
không bỏ sót lịch sử. Replay 140 PDF cũ đạt 140 READY / 0 NOT_OBSERVED / 0
UNRESOLVED. Có 31 dòng cùng bản chất với 19 dòng ABB/LPB/STB/VBB ở trên:
`Công ty TNHH từ hai thành viên trở lên có vốn Nhà nước trên 50% hoặc Nhà nước
giữ quyền chi phối`. Tất cả đều có parent `Tiền gửi của tổ chức kinh tế`; schema
tiền gửi chỉ có 1079 cho **một thành viên**, còn 770 thuộc nhánh cho vay.

**Lý do chung của từng dòng:** `CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT` và
`KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG`.

| Ngân hàng | Kỳ / báo cáo | File PDF | Trang | Khoản mục thực tế |
|---|---|---|---:|---|
| VIB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 49 | `Công ty TNHH 2 thành viên trở lên... vốn nhà nước trên 50%...` |
| VIB | 6 tháng/2025 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf>) | 49 | Cùng khoản mục trên |
| VIB | 9 tháng/2025 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 9 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Công ty mẹ Soát xét 9 tháng đầu năm 2025.pdf>) | 48 | Cùng khoản mục trên |
| VIB | Quý 2/2025 · Công ty mẹ · Chưa kiểm toán | [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf>) | 43 | Cùng khoản mục trên |
| VIB | Quý 4/2025 · Công ty mẹ · Chưa kiểm toán | [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf>) | 43 | Cùng khoản mục trên |
| VIB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 47 | Cùng khoản mục trên |
| VIB | 6 tháng/2025 · Hợp nhất · Soát xét | [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf>) | 47 | Cùng khoản mục trên |
| VIB | 9 tháng/2025 · Hợp nhất · Soát xét | [BCTC Hợp nhất Soát xét 9 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét 9 tháng đầu năm 2025.pdf>) | 46 | Cùng khoản mục trên |
| VIB | Quý 2/2025 · Hợp nhất · Chưa kiểm toán | [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf>) | 43 | Cùng khoản mục trên |
| VIB | Quý 4/2025 · Hợp nhất · Chưa kiểm toán | [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../../../vietstock_bctc/VIB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf>) | 43 | Cùng khoản mục trên |
| VIB | 6 tháng/2026 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf](<../../../../vietstock_bctc/VIB/2026/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf>) | 46 | Cùng khoản mục trên |
| VIB | Quý 1/2026 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét quý 1 năm 2026.pdf](<../../../../vietstock_bctc/VIB/2026/BCTC Công ty mẹ Soát xét quý 1 năm 2026.pdf>) | 46 | Cùng khoản mục trên |
| VIB | Quý 2/2026 · Công ty mẹ · Chưa kiểm toán | [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../../../vietstock_bctc/VIB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf>) | 42 | Cùng khoản mục trên |
| VIB | 6 tháng/2026 · Hợp nhất · Soát xét | [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf](<../../../../vietstock_bctc/VIB/2026/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf>) | 45 | Cùng khoản mục trên |
| VIB | Quý 1/2026 · Hợp nhất · Soát xét | [BCTC Hợp nhất Soát xét quý 1 năm 2026.pdf](<../../../../vietstock_bctc/VIB/2026/BCTC Hợp nhất Soát xét quý 1 năm 2026.pdf>) | 45 | Cùng khoản mục trên |
| VIB | Quý 2/2026 · Hợp nhất · Chưa kiểm toán | [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../../../vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf>) | 42 | Cùng khoản mục trên |
| VPB | Quý 3/2025 · Hợp nhất · Chưa kiểm toán | [1-bctc-hop-nhat.pdf](<../../../../vietstock_bctc/VPB/2025/1-bctc-hop-nhat.pdf>) | 57 | `Công ty TNHH 2 thành viên trở lên... vốn Nhà nước trên 50%...` |
| VPB | Quý 3/2025 · Riêng lẻ · Chưa kiểm toán | [2-bctc-rieng-le.pdf](<../../../../vietstock_bctc/VPB/2025/2-bctc-rieng-le.pdf>) | 49 | Cùng khoản mục trên |
| VPB | Năm 2025 · Công ty mẹ · Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 53 | Cùng khoản mục trên |
| VPB | 6 tháng/2025 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf>) | 53 | Cùng khoản mục trên |
| VPB | Quý 1/2025 · Công ty mẹ · Chưa kiểm toán | [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf>) | 46 | Cùng khoản mục trên |
| VPB | Quý 2/2025 · Công ty mẹ · Chưa kiểm toán | [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf>) | 47 | Cùng khoản mục trên |
| VPB | Năm 2025 · Hợp nhất · Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 61 | Cùng khoản mục trên |
| VPB | Quý 1/2025 · Hợp nhất · Chưa kiểm toán | [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf>) | 58 | Cùng khoản mục trên |
| VPB | Quý 2/2025 · Hợp nhất · Chưa kiểm toán | [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../../../vietstock_bctc/VPB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf>) | 57 | Cùng khoản mục trên |
| VPB | Quý 4/2025 · Hợp nhất · Chưa kiểm toán | [Bctc-hop-nhat-1901.pdf](<../../../../vietstock_bctc/VPB/2025/Bctc-hop-nhat-1901.pdf>) | 57 | Cùng khoản mục trên |
| VPB | Quý 4/2025 · Riêng lẻ · Chưa kiểm toán | [bctc-rieng-le.pdf](<../../../../vietstock_bctc/VPB/2025/bctc-rieng-le.pdf>) | 49 | Cùng khoản mục trên |
| VPB | Quý 2/2026 · Hợp nhất · Chưa kiểm toán | [1.-BCTC-hop-nhat.pdf](<../../../../vietstock_bctc/VPB/2026/1.-BCTC-hop-nhat.pdf>) | 53 | Cùng khoản mục trên |
| VPB | Quý 2/2026 · Riêng lẻ · Chưa kiểm toán | [2.-BCTC-rieng-le.pdf](<../../../../vietstock_bctc/VPB/2026/2.-BCTC-rieng-le.pdf>) | 47 | Cùng khoản mục trên |
| VPB | Quý 1/2026 · Riêng lẻ · Chưa kiểm toán | [4-bctc-rieng-le-ban-tra-cuu.pdf](<../../../../vietstock_bctc/VPB/2026/4-bctc-rieng-le-ban-tra-cuu.pdf>) | 48 | Cùng khoản mục trên |
| VPB | 6 tháng/2026 · Công ty mẹ · Soát xét | [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf](<../../../../vietstock_bctc/VPB/2026/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf>) | 54 | Cùng khoản mục trên |

## Những mục đã được giải quyết, không còn nằm trong ledger

- Bốn báo cáo STB có `Tiền gửi đảm bảo thanh toán khác` đã map đủ 1072, 1073,
  1074; không còn SOURCE_ONLY.
- `Tiền gửi tiết kiệm` đã map 1063 bằng tổng đúng các dòng tiết kiệm có kỳ hạn
  và không kỳ hạn nhìn thấy. Không tạo child 1064/1065 nếu PDF không có bằng
  chứng theo VND/ngoại tệ.
- `Tiền gửi ký quỹ` đã map 1066 và các child 1067/1068 khi có công bố.
- Các biến thể `Đơn vị: đồng`, `Đvt: triệu đồng`, header nằm ở fragment/trang
  liền trước, bảng continuation và `Số dư cuối quý` đã được xử lý bằng gate
  generic có test dương và test tamper âm.
- Hai PDF VPB cũ có bảng lãi suất mà JSON bỏ mất câu dẫn và gắn cột thành
  `TEXT/Triệu đồng`. Bảng chỉ được loại khỏi mapping tiền khi **mọi** cell nằm
  trong 0–100 và có ít nhất một dải như `0,30 - 8,50`; bỏ dải hoặc đưa một giá
  trị vượt bound thì document quay về UNRESOLVED. PDF trang 53 của cả hai báo
  cáo đã được kiểm tra trực quan.
- Không còn khoản mục nhìn thấy, có ReportNormId cùng bản chất, nhưng bị bỏ lại
  chỉ vì khác cách gọi, layout, slicing, continuation, header hoặc đơn vị.

## Kiểm tra hồi quy và bằng chứng kỹ thuật

- Full 271 terminal sau null-veto/source repair:
  `/dev/shm/family15-full271-v18.json`; SHA-256
  `b1d25bdd7da25dcc0f1bbace1375b55527fa1a4d560d04caebdf4a112bdc5014`;
  sweep `gjfafsv1:sweep:a514e97ba258101100954bd7880bd38b923870a1e6a08fdcc7b4b2a7023b558f`.
- Audit replay: `/dev/shm/family15-full271-v18.audit.json`; SHA-256
  `2b44c2b0f536c625141391b211402b8994a83adf742cb42bc1132fd4bbede023`;
  264 cluster, 1.184 equation, 3.898 mapping và 6 source repair. Ingest
  source-replay terminal thành công với run id
  `gjfafstorev1:run:22e0d421e2ae06dfa6fbfd1a439245573ee48ba56600d3428d9581a9e1654c1e`.
- Global source-observation audit đạt `PASS`: 0 violation, 0 mapping partial,
  0 ô blank trong mapping và không có role mà mọi lane đều không quan sát.
  Walker thấy 7.796 occurrence / 15.592 cell vì sweep lưu cùng mapping ở
  candidate và trial; trục mapping audit chuẩn vẫn là 3.898.
- Differential so với v14 có 0 thay đổi status/reason, 0 thay đổi trục role và
  0 thay đổi coefficient. Sáu cell ở ordinal 243/246/248/249/252 đổi duy nhất
  từ `INFERRED_BLANK_ZERO*` sang `DASH_ZERO` có source text `-`; 32 mapping
  source-ref ở tám PDF BAB bỏ tham chiếu tới các hàng currency-subtype trống cả
  hai lane. Differential receipt SHA-256
  `a444f7a8e5418b9f049a2b34b17d4fe300ea3de5284ef4d63cb04c78c6d9fbfb`.
- Hồi quy 140 PDF của 8 ngân hàng cũ: **140 READY / 0 NOT_OBSERVED / 0
  UNRESOLVED / 2.189 mapping**. Status, candidate count và reasons của cả 140
  PDF giữ nguyên. So với release cũ 2.206 mapping, thay đổi ròng -17 được đối
  chiếu đầy đủ: bỏ 29 mapping sai RNID770 chéo nhánh cho vay; bỏ 12 child
  1064/1065 từng được suy ra dù PDF ACB chỉ công bố aggregate tiết kiệm; thêm
  24 leaf khách hàng nhìn thấy ở hai PDF VPB 2026 trước đây bị bỏ cả subtable.
  Frozen release pin cũ không bị sửa.
- Output hồi quy old8 OFFICIAL terminal: `/dev/shm/family15-old8-v18.json`;
  SHA-256
  `d5a6492a72b5eac32377dcdd6e7914b42ef11844b512c0a003349cb92caca71f`;
  audit SHA-256
  `718e06318b5eee0a0c4b5f77dc244b9470a05639c078bc16744f63e43447ba93`.
  Sweep `gjfafsv1:sweep:d2c25fd458aac55edeac8d3daba1426a7caa23f92b84851a73607e8b3fed15b0`
  và ingest source-replay run
  `gjfafstorev1:run:fd7f620ee3fe2e97033af45ade4c77290362dc6d4a882adc23fa26cdf733962d`.
  Global source-observation gate cũng `PASS` với 0 violation; differential
  so với old8 v3 có 0 thay đổi status/reason và 0 thay đổi role/coefficient.
- 76 test tập trung cho engine, indexed wiring, source-observation gate và
  runner đều đạt; có test dương
  và tamper âm cho split table/page, unit carrier, mixed period/unit,
  subtotal composition, blank zero, schema parent branch và replay order.
- Kiểm thử tích hợp xác nhận helper đơn vị dùng chung vẫn compile được family
  phân cấp chỉ chấp nhận triệu đồng; compiler riêng của Family 15 vẫn khóa đúng
  hai đơn vị nguồn `MILLION_VND` và `VND`. Rerun full-271 sau kiểm thử này giữ
  nguyên các status, role và coefficient của output v14; khác biệt provenance
  chỉ gồm sáu repair có xác thực và các source-ref trống bị loại nêu trên.
- Ruff check và `git diff --check` đều đạt trên các file Family 15.
- Ảnh kiểm tra trực quan 7 PDF UNRESOLVED:
  `/dev/shm/f15-residual-pages/final-unresolved-contact.png`.
- Ảnh kiểm tra trực quan toàn bộ 23 PDF READY có residual:
  `/dev/shm/f15-source-only-pages/{ABB,LPB,NVB,STB,VBB}-contact.png`.

Các SHA và tên artifact chỉ đặt ở cuối để truy vết kỹ thuật; nhận diện chính ở
trên luôn là ngân hàng, kỳ, loại báo cáo, tên PDF, trang và khoản mục thực tế.
