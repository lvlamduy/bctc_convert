# Family 17 – Góp vốn, đầu tư dài hạn khác

## Kết quả chốt trên corpus 271 PDF (2025–2026)

| PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED | Mapping | Phương trình |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 271 | 195 | 76 | 0 | 584 | 404 |

- Cấu trúc schema được map: tổng giá trị thuần (RNID 862), đầu tư vào công ty liên doanh (6066), công ty liên kết (6067), đầu tư dài hạn khác (867), tổ chức kinh tế/dự án dài hạn (5960), quỹ đầu tư (5961) và dự phòng giảm giá đầu tư dài hạn (5959).
- 76 `NOT_OBSERVED` giữ nguyên so với checkpoint trước: không có cụm bảng thuộc family trong phạm vi JSON đã chọn. Việc sửa ô trống không làm một PDF vắng family biến thành lỗi.
- Không còn `UNRESOLVED`; không còn trạng thái suy số 0 từ ô nguồn trống.
- Hợp đồng kiểm tra nguồn trên artifact hoàn chỉnh: `PASS`, 0 vi phạm. Mỗi giá trị 0 mới trong 14 trường hợp dưới đây đều xuất phát từ dấu gạch ngang nhìn thấy trên PDF, không phải từ phương trình.

## 14 trang có dấu gạch ngang bị JSON nguồn bỏ sót

Mỗi sửa chữa dưới đây được khóa bằng SHA của PDF, phiên bản JSON trang, SHA ảnh render, số trang, section/table, hàng, cột và giá trị gốc phải đúng `null`. Overlay chỉ được phép chép literal `-` sang bản sao của JSON; lệch bất kỳ khóa nào thì dừng.

| Ngân hàng | File PDF dễ nhận biết | Trang | Khoản mục/cột được sửa | Kết luận |
| --- | --- | ---: | --- | --- |
| ABB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | 19 | Liên doanh; liên kết; dự phòng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| ABB | `BCTC Hợp nhất quý 4 năm 2025__592d2993__3_abb_2026_2_4_91abe48_bctc_hn_q4_2025.pdf` | 19 | Liên doanh; liên kết; dự phòng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| ABB | `phpnjkobf-bctc-q2-2025-hn-6889fad62c419.pdf` | 19 | Liên doanh; liên kết; dự phòng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| EIB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | 24 | Liên doanh; liên kết; đầu tư dài hạn khác; dự phòng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| STB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 31 | Liên doanh; liên kết – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| TCB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | 40 | Đầu tư vào công ty liên kết – giá gốc, cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| TCB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | 49 | Đầu tư vào công ty liên kết – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| TCB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 50 | Đầu tư vào công ty liên kết – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| TPB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | 43 | Đầu tư dài hạn khác; tổng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| VAB | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | 34 | Liên doanh; liên kết; dự phòng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| VAB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | 36 | Liên doanh; liên kết – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| VAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 36 | Liên doanh; liên kết – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| VAB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | 36 | Liên doanh; liên kết – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |
| VBB | `000000014895152_VI_BaoCaoTaiChinh_HopNhat_Q1_2025.pdf` | 17 | Liên doanh; liên kết; đầu tư dài hạn khác; dự phòng; tổng – cột so sánh | PDF có dấu gạch ngang, JSON ghi `null`; sửa thành `DASH_ZERO`. |

Tổng cộng: **14 trang, 34 ô sửa nguồn**. So với artifact cũ, 32 ô từng mang trạng thái `INFERRED_BLANK_ZERO_IF_EQUATION_EXACT` nay có bằng chứng dấu gạch ngang thật; hai mapping VAB quý 3/2025 (liên doanh và liên kết) được khôi phục vì cả hai kỳ đều có dấu gạch ngang thật. Không có mapping nào bị mất.

## Phân biệt với ô trống thật trong bộ hồi quy 8 ngân hàng cũ

Các trường hợp sau đã kiểm tra ảnh PDF và phải giữ là ô trống, tuyệt đối không đổi thành 0:

| Ngân hàng | File PDF | Trang | Khoản mục | Xử lý đúng |
| --- | --- | ---: | --- | --- |
| HDB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | 36 | Đầu tư vào công ty liên doanh, cả hai kỳ | Bỏ mapping của riêng role này; vẫn giữ tổng nhìn thấy với phương trình ghi `INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL`. |
| HDB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | 41 | Đầu tư vào công ty liên doanh, cả hai kỳ | Như trên. |
| HDB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | 35 | Đầu tư vào công ty liên doanh, cả hai kỳ | Như trên. |
| HDB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | 27 | Đầu tư vào công ty liên kết: kỳ hiện tại trống, kỳ so sánh 658.075 | Giữ mapping một phần `[null, 658.075]`; ô trống mang `BLANK_SOURCE_CELL`. |

Kết quả hồi quy strict: **140 READY / 0 NOT_OBSERVED / 0 UNRESOLVED**, 431 mapping, 480 phương trình; 57/57 giá trị oracle lịch sử khớp chính xác. Ba role trống hoàn toàn bị bỏ, một role quan sát một phần được giữ, và các tổng nhìn thấy không bị mất.

## Gate kỹ thuật

- Artifact sửa nguồn: 14 repair receipt duy nhất, mỗi receipt được áp đúng một lần; thiếu, thừa hoặc lặp đều bị từ chối.
- Test phá hoại bao phủ: hash artifact sai; source/path lệch; page JSON version lệch; ảnh render lệch; base page/table/row/cột/giá trị gốc lệch; sửa không đủ hoặc áp lặp.
- Overlay chỉ sửa clone, không thay đổi JSON nguồn đã lưu.
- Chỉ literal dấu gạch ngang được chấp nhận; không có đường đưa số từ phương trình vào ô nguồn.
