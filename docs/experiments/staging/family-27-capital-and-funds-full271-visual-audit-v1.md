# Family 27 — Vốn và các quỹ / Biến động vốn chủ sở hữu

## Phạm vi và kết quả

Checkpoint này chỉ dùng báo cáo từ năm 2025 đến hiện tại. Hai tập được kiểm tra độc lập vì chúng là hai trục nguồn khác nhau:

| Tập báo cáo | PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED | Ghi chú |
| --- | ---: | ---: | ---: | ---: | --- |
| 19 ngân hàng mở rộng | 271 | 252 | 0 | 19 | Từ baseline 211 READY / 60 UNRESOLVED; đã kiểm tra ảnh PDF của toàn bộ residual |
| 8 ngân hàng cũ | 140 | 139 | 0 | 1 | Hồi quy độc lập; hai lỗi chép JSON ở BID và VIB đã được đối chiếu lại với PDF |
| **Tổng hai trục không trùng ngân hàng** | **411** | **391** | **0** | **20** | READY + NOT_OBSERVED + UNRESOLVED = PDF khảo sát |

`NOT_OBSERVED = 0` không phải do ép trạng thái: cả 411 PDF trong hai tập chuyên biệt này đều có bảng vốn chủ sở hữu đúng family. Các trường hợp còn lại là nội dung có thật trên PDF nhưng chính nguồn PDF tự mâu thuẫn, hoặc không có bằng chứng đơn vị đủ chắc chắn.

## Cấu trúc chung đã nhận diện và map

Family nhận diện bảng biến động vốn theo hai hướng trình bày: khoản mục vốn nằm ở cột hoặc khoản mục vốn nằm ở hàng. Hệ thống giữ đúng các ô nhìn thấy, ghép tối đa một trang tiếp nối có bằng chứng liền kề, và map theo thứ tự schema:

- `1128` Vốn và các quỹ — khoản mục cha của family.
- `1129` Số dư đầu kỳ; `1141` Số dư cuối kỳ.
- `6019` Tổng tăng; `6020` Tổng giảm, chỉ khi dòng tăng/giảm được quan sát và quan hệ được xác định chắc chắn.
- `5984` Vốn điều lệ; `6011` Thặng dư vốn cổ phần; `6012` Vốn khác; `6013` Quỹ dự trữ bổ sung vốn điều lệ; `6014` Quỹ dự phòng tài chính; `6015` Quỹ khác; `6016` Chênh lệch tỷ giá; `6017` Lợi nhuận chưa phân phối; `6018` Lợi ích cổ đông không kiểm soát.

Biến thể đã xử lý gồm tiêu đề tiếng Việt/tiếng Anh, “số đầu/cuối kỳ, quý, năm”, bảng ngang/dọc, nhóm bổ sung “các quỹ của TCTD”, cột tổng cộng, trang tiếp nối, và đơn vị VND hoặc triệu VND khi có bằng chứng trực tiếp. Ô trống vẫn là `null`; chỉ dấu gạch nhìn thấy trên PDF mới là số 0 được quan sát. Phương trình chỉ dùng để kiểm tra hoặc bác bỏ, không dùng để tự sinh số.

## Ledger UNRESOLVED — từng PDF cần mở kiểm tra

Số trang dưới đây là số trang vật lý của PDF dùng trong ứng dụng; số trang in ở chân trang có thể khác.

| # | Ngân hàng | Kỳ / báo cáo | Kiểm toán | Tên file PDF | Trang PDF | Khoản mục nhìn thấy / khoản mục cha | Schema gần nhất | Vì sao chưa map chắc chắn | Phân loại nguyên nhân |
| ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| 1 | ABB | Quý 2/2026, riêng lẻ | Không ghi trong tên file | `phpnchaip-bao-cao-tai-chinh-rieng-le-quy-ii-nam-2026-6a5df290b2d0a.pdf` | 21 | `Số dư cuối kỳ` trong bảng biến động vốn; cha: Vốn và các quỹ | `1141`, cùng các ID thành phần `5984`, `6011`–`6018` | Các thành phần cuối kỳ cộng được 22.597.211 nhưng PDF in tổng 22.597.210, lệch 1. Không sửa tròn và không chọn một giá trị thay PDF. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 2 | NVB | Quý 4/2025, hợp nhất | Không ghi trong tên file | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 43 | Dòng tăng vốn và `Số dư cuối kỳ`; cha: Vốn và các quỹ | `5984`, `1141`, `6019` | Số đầu 6.092.846 cộng tăng vốn 7.500.000 bằng 13.592.846, nhưng PDF in số cuối 13.592.924, chênh 78. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 3 | PGB | Quý 3/2025, riêng lẻ | Không ghi trong tên file | `3_pgb_2025_10_22_8eac562_vi_baocaotaichinh_q3_2025.pdf` | 35–36 | Quỹ dự phòng tài chính, quỹ dự trữ bổ sung vốn điều lệ và tổng các quỹ; cha: Vốn và các quỹ | `6013`, `6014`, `6015`, `1141` | Bảng chính trang 35 in 311.990 / 75.577, bảng chi tiết quỹ trang 36 in 311.991 / 75.576; hai bảng cùng PDF xung đột dù tổng không đổi. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 4 | PGB | Quý 4/2025, riêng lẻ | Không ghi trong tên file | `4_pgb_2026_1_22_d793078_vi_baocaotaichinh_q4_2025.pdf` | 35–36 | Quỹ dự phòng tài chính, quỹ dự trữ bổ sung vốn điều lệ và tổng các quỹ; cha: Vốn và các quỹ | `6013`, `6014`, `6015`, `1141` | Cùng mẫu xung đột giữa bảng vốn trang 35 và bảng chi tiết quỹ trang 36: 311.990 / 75.577 so với 311.991 / 75.576. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 5 | PGB | Quý 1/2025, riêng lẻ | Không ghi trong tên file | `BCTC quý 1 năm 2025.pdf` | 35–36 | Quỹ dự phòng tài chính và tổng các quỹ; cha: Vốn và các quỹ | `6014`, `6015`, `1141` | Bảng chính in 278.010, bảng chi tiết in 278.011; riêng tổng các thành phần trang 36 bằng 320.257 nhưng PDF in 320.256. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 6 | PGB | Quý 1/2026, riêng lẻ | Không ghi trong tên file | `1_pgb_2026_4_28_15bbc70_vi_baocaotaichinh_q1_2026.pdf` | 35–36 | `Tăng vốn`, quỹ dự trữ bổ sung vốn điều lệ và tổng; cha: Vốn và các quỹ | `6013`, `6019`, `1141` | Hai bảng lệch quỹ 75.576/75.577; đồng thời 1.315.912 trừ 14 bằng 1.315.898 nhưng PDF in tổng tăng 1.315.897. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 7 | SHB | Quý 2/2026, công ty mẹ | Không ghi trong tên file | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | 34 | `Quỹ khác` và `Số dư cuối kỳ`; cha: Vốn và các quỹ | `6015`, `1141` | 182.058 + 118.494 − 28.167 bằng 272.385 nhưng PDF in 272.386, lệch 1. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 8 | SHB | Quý 2/2026, hợp nhất | Không ghi trong tên file | `BCTC Hợp nhất quý 2 năm 2026.pdf` | 35 | Dòng giảm, `Quỹ khác` và tổng cuối kỳ; cha: Vốn và các quỹ | `6015`, `6020`, `1141` | Sau khi chép đúng các dấu gạch từ PDF, tổng giảm thành phần là -382.577 nhưng PDF in -382.576; quỹ khác tính 290.765 nhưng in 290.387; tổng toàn bảng lệch 379. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 9 | STB | Quý 2/2025, công ty mẹ | Không ghi trong tên file | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | 37 | `Số dư cuối kỳ`, chủ yếu lợi nhuận chưa phân phối; cha: Vốn và các quỹ | `6017`, `1141` | Các thành phần cuối kỳ cộng 58.939.080 nhưng PDF in 58.939.079, lệch 1. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 10 | STB | Quý 2/2025, hợp nhất | Không ghi trong tên file | `BCTC Hợp nhất quý 2 năm 2025.pdf` | 42 | `Số dư cuối kỳ`; cha: Vốn và các quỹ | `1141`, các ID thành phần | 54.972.070 + 5.790.290 + 184.938 − 1.130.094 + 4.002 bằng 59.821.206 nhưng PDF in 59.821.207. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 11 | STB | Quý 4/2025, hợp nhất; bảng tiếng Anh | Không ghi trong tên file | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 41 | `Others`, retained earnings và closing total; cha: Statement of changes in owners' equity | `6015`, `6017`, `1141` | Dòng Others: -125 + 971 bằng 846 nhưng PDF in 845; số cuối của retained earnings và tổng toàn bảng cũng lệch 1. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 12 | VAB | Quý 1/2025, hợp nhất | Không ghi trong tên file | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | 38–39 | Tổng đầu kỳ, tăng/giảm và tổng cuối kỳ; cha: Vốn và các quỹ | `1129`, `6019`, `6020`, `1141` | 8.856.678 + 1.003.262 − 708.079 bằng 9.151.861 nhưng PDF in 9.151.860; dấu của dòng giảm không đủ nhất quán để chọn cách diễn giải khác. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 13 | VAB | Quý 3/2025, công ty mẹ | Không ghi trong tên file | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | 39–40 | Tổng đầu/tăng/giảm/cuối và vốn điều lệ; cha: Vốn và các quỹ | `1129`, `5984`, `6019`, `6020`, `1141` | 8.797.270 + 6.237.414 − 5.423.261 bằng 9.611.423 nhưng PDF in 9.611.424; một thành phần vốn cũng lệch 1. PDF không khóa được đơn vị family trong tài liệu có nhiều đơn vị. | `NGUỒN PDF TỰ MÂU THUẪN`; `KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ` |
| 14 | VAB | Quý 4/2025, công ty mẹ | Không ghi trong tên file | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | 39–40 | Tổng tăng/giảm/cuối và các thành phần; cha: Vốn và các quỹ | `6019`, `6020`, `1141`, các ID thành phần | Đã sửa đúng token nhìn thấy `216.502`, nhưng PDF vẫn có nhiều phương trình lệch 1–2 và không có bằng chứng đơn vị family đủ chặt. | `NGUỒN PDF TỰ MÂU THUẪN`; `KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ` |
| 15 | VAB | Quý 2/2025, hợp nhất | Không ghi trong tên file | `BCTC HOP NHAT QUY 2.2025 TVIET_0001-da nen.pdf` | 37–38 | Toàn bảng biến động vốn; cha: Vốn và các quỹ | `1128` và toàn bộ nhánh `1129`, `1141`, `5984`, `6011`–`6020` | Số và quan hệ trong bảng khép, nhưng trang/section không ghi đơn vị và tài liệu dùng nhiều đơn vị. Không được suy đơn vị từ trang gần nhất. | `KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ` |
| 16 | VAB | Quý 3/2025, hợp nhất | Không ghi trong tên file | `BCTC Hợp nhất quý 3 năm 2025.pdf` | 40 | Tổng tăng/giảm/cuối và các thành phần; cha: Vốn và các quỹ | `6019`, `6020`, `1141` | Các tổng ngang và quan hệ đầu kỳ ± biến động = cuối kỳ trên PDF không đồng thời khớp; cách hiểu dấu giảm cũng xung đột. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 17 | VAB | Quý 4/2025, hợp nhất | Không ghi trong tên file | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 40 | Tổng tăng/giảm/cuối và các thành phần; cha: Vốn và các quỹ | `6019`, `6020`, `1141` | Các tổng ngang và dọc trên PDF không đồng thời khớp; không có một cách đặt dấu duy nhất giải được bảng. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 18 | VAB | Quý 2/2025, riêng lẻ | Không ghi trong tên file | `BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf` | 37–38 | Tổng tăng/giảm/cuối và các thành phần; cha: Vốn và các quỹ | `6019`, `6020`, `1141` | Các số in trên PDF tạo nhiều sai lệch cộng dồn; quan hệ dấu của biến động giảm không xác định chắc chắn. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 19 | VAB | Quý 2/2026, công ty mẹ | Không ghi trong tên file | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | 40 | Lợi nhuận chưa phân phối, dòng giảm và tổng cuối kỳ; cha: Vốn và các quỹ | `6017`, `6020`, `1141` | Dòng giảm đặt trong ngoặc nhưng quan hệ với số cuối không nhất quán; tổng toàn bảng lệch 1. | `NGUỒN PDF TỰ MÂU THUẪN` |
| 20 | BID | Năm 2025, hợp nhất | Kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 53 | `Tăng/(Giảm) khác` trong báo cáo thay đổi vốn; cha: Vốn và các quỹ | `6019`/`6020`, `6012`–`6018` | Các ô thành phần -349 + 1.710 − 26 + 9.087 − 10.231 bằng 191, nhưng PDF in tổng dòng là -1.505. Đây là mâu thuẫn ngay trên PDF, không phải lỗi OCR còn có thể sửa bằng alias. | `NGUỒN PDF TỰ MÂU THUẪN` |

Không có dòng ledger trùng nhau: khóa kiểm tra là tập nguồn + ngân hàng + tên file + trang PDF.

## SOURCE_ONLY trong PDF READY

Các dòng sau vẫn nhìn thấy trên PDF và được giữ trong receipt để người đọc kiểm tra, nhưng không được ép vào ID của bảng biến động vốn:

| Dòng/nhóm trên PDF | 19 ngân hàng: số lần | 8 ngân hàng cũ: số lần | Kết luận dễ hiểu |
| --- | ---: | ---: | --- |
| Chênh lệch đánh giá lại tài sản | 33 | 12 | Có ID gần nghĩa ở bảng cân đối, nhưng không có child cùng bản chất trong nhánh biến động vốn Family 27. |
| Vốn đầu tư xây dựng cơ bản | 66 | 16 | Khoản mục chi tiết/kiểm soát ngoài tập child được schema Family 27 cho phép. |
| Quỹ đầu tư phát triển | 154 | 84 | Là chi tiết của nhóm quỹ ở nhiều mẫu ngân hàng; schema Family 27 không có child riêng tương đương để map trực tiếp. |
| Quỹ của TCTD | 36 | 0 | Là dòng nhóm/tổng kiểm soát; các child quỹ phù hợp bên dưới vẫn được map vào `6013`–`6015`. Không map lặp dòng nhóm. |
| Khoản mục “Khác” không xác định cụ thể | 1 | 0 | Tên nguồn không đủ để chọn một child duy nhất. |
| Cổ phiếu quỹ | 85 | 38 | Có ID gần nghĩa ở nhánh số dư vốn khác, nhưng không phải child cùng ngữ cảnh của matrix Family 27; không dùng chéo chỉ vì trùng tên. |
| **Tổng số lần xuất hiện SOURCE_ONLY** | **375** | **150** | Đây là dữ liệu nguồn được bảo toàn, không phải `NOT_OBSERVED` và không phải thiếu alias/layout. |

Tổng cộng có 190/271 PDF của tập 19 ngân hàng và 94/140 PDF của tập 8 ngân hàng chứa ít nhất một dòng SOURCE_ONLY. Một PDF có thể có nhiều dòng, nên số lần xuất hiện lớn hơn số PDF.

## Các sửa nguồn JSON đã được xác thực bằng ảnh PDF

Có 12 trang mà JSON chọn sẵn bị lệch hàng/cột, thiếu dấu gạch hoặc thiếu đơn vị dù PDF nhìn rõ. Hệ thống chỉ áp bản chép lại trên một bản sao, khóa đúng file, trang, section, table, hàng, cột, ảnh toàn trang và crop; sai/mất/thừa/tamper đều fail closed. Các trang thuộc BID, LPB, MBB, MSB, SHB, TPB, VAB, VCB và VIB. Không số nào được suy ngược từ phương trình.

Hai correction hồi quy đáng chú ý:

- BID, `BCTC Hợp nhất quý 1 năm 2026.pdf`, trang 26: PDF cho thấy `(98)` và `982` thuộc dòng chênh lệch tỷ giá; `(77)` và `70.268` thuộc dòng tăng/(giảm) khác. JSON ban đầu dồn các ô sang sai hàng.
- VIB, `BCTC Hợp nhất Soát xét quý 1 năm 2025.pdf`, trang 50: PDF in dấu gạch ở toàn bộ ô trống có nghĩa số 0; JSON ban đầu bỏ dấu gạch và lặp nhầm `10.556`, `(150.000)` sang hàng khác.

## Kiểm tra kỹ thuật cuối

- Bộ test evaluator/indexed chuyên Family 27: 116 test đạt; thêm 19 test dùng chung cho source-observation; Ruff đạt.
- Contract “ô nhìn thấy mới được map”: đạt cho toàn bộ 391 PDF READY; ô nguồn trống giữ `null`, dấu gạch nguồn giữ trạng thái zero quan sát.
- Replay truy vấn và replay candidate chạy lại từ store/index bất biến cho cả hai trục; không dùng provider.
- Bộ replay cũng kiểm tra riêng trục biến động của bảng quỹ bổ sung: chỉ các lane thật sự có trong bảng bổ sung được map; xóa hoặc làm trùng lane đều bị từ chối.
- Chi tiết SHA/receipt chỉ dùng để truy vết kỹ thuật trong artifact kết quả, không dùng làm tên nhận diện chính trong ledger này.

### Truy vết kỹ thuật

- Kết quả 19 ngân hàng: `/dev/shm/f27-full271-final-v15-lower-level.json`, SHA-256 `0fa70a4e2efa43b95f0eaaeab94703be61d2fc2274a1b22fdb245c83bec7a1cc`; indexed evidence SHA-256 `5a2fdfb0016d0abc0515527317bfe75c9c67678aed1fc6908edd93ff1f742c9a`.
- Kết quả 8 ngân hàng cũ: `/dev/shm/f27-old140-final-v15-lower-level.json`, SHA-256 `2b3f6575885b865edb20ad80d1d26eb4323edac66c0f86c27043b1af9c7458d7`; indexed evidence SHA-256 `eb75293d6535b22ab409782ce4be45e70d8f6a1915918e5abb82c7140ab67f77`.
- Engine Family 27 dùng cho replay: SHA-256 `244aeda11d5774fa43acd475f9142bd363f20c8e2c34a2554aceeeaee78e47a6`.
- Artifact chép lại 12 trang PDF: SHA-256 `4ff68eb6a3a1953cc042cac7521fb46f2eeb407559909e976e87712784caa68d`.
