# Dashboard family thuyết minh — bản dễ đọc

Cập nhật: 2026-09-01. Phạm vi ngân hàng: ACB, BID, CTG, HDB, MBB, VCB,
VIB và VPB.

Đây là bản đọc nhanh, chỉ phản ánh kết quả hiện hành. Không dùng mã chạy, SHA
hay tên artifact để nhận diện family. Bằng chứng và lịch sử kỹ thuật vẫn được
giữ trong [`COMPLETED_TM_FAMILIES.md`](COMPLETED_TM_FAMILIES.md).

Quy ước:

- **READY**: phần thuộc schema của family đã map và qua các phép kiểm tra hiện hành.
- **NOT_OBSERVED**: family không xuất hiện trong đúng phạm vi PDF đã khảo sát;
  đây không phải lỗi.
- **UNRESOLVED**: có nội dung nguồn nhưng chưa thể kết luận mapping/cấu trúc.
- **SOURCE_ONLY**: nội dung nhìn thấy nhưng không map vào family đang xét; xem
  [`UNRESOLVED_MAPPING_LEDGER_READABLE.md`](UNRESOLVED_MAPPING_LEDGER_READABLE.md#source-only).

## Tổng quan

- **54 family** đã chạy đủ **140 PDF/family**: **7.560 lượt family–PDF =
  5.139 READY + 2.406 NOT_OBSERVED + 15 UNRESOLVED**.
- Family **Thu nhập từ lãi thuần** mới có checkpoint riêng trên 8 BCTC hợp
  nhất kiểm toán năm 2025: **8 READY, 0 NOT_OBSERVED, 0 UNRESOLVED**.
- Chỉ còn bốn family có PDF `UNRESOLVED`: **Vốn và các quỹ (3), Thu nhập nhân
  viên (6), Thu nhập lãi (4), Chi phí hoạt động (2)**.

## Checkpoint rà soát schema theo chỉ đạo ngày 2026-09-01

Rà lại đủ 140 PDF của tám ngân hàng cho các family được nêu trong yêu cầu mới
cho thấy hai loại kết quả khác nhau:

- **Đã map đúng nhưng màn hình cũ báo nhầm:** biến động dự phòng cho vay (140/140
  PDF), tiền gửi khách hàng (140/140), TSCĐ hữu hình (72 PDF có bảng), TSCĐ vô
  hình (72), bất động sản đầu tư (12) và phát hành giấy tờ có giá (140). Lớp xem
  kết quả trước đây không đọc hết tham chiếu trang/bảng/dòng của mapping tổng hợp.
  Lỗi trình bày này đã được sửa; dòng đối chiếu nay ghi rõ “ID đã map từ nguồn
  khác”, không còn bị gọi là “chưa map”.
- **Quy tắc schema đã được bổ sung, cần replay family để trở thành mapping lưu
  chính thức:** 29 PDF có `Dự phòng giảm giá chứng khoán kinh doanh` → ID 612;
  7 PDF có 28 dòng phân loại niêm yết → ID 618/619/621/622; 13 PDF có 31 dòng
  đối tượng doanh nghiệp → ID 775/776/780/782. Các dòng này hiện được màn hình
  ghi riêng là “Có trên PDF nhưng chưa map”, không còn bị xếp SOURCE_ONLY hay
  kết luận nhầm là thiếu schema.

Các kiểm tra cụ thể đã xác nhận:

- `Tiền gửi tiết kiệm không kỳ hạn` và `Tiền gửi tiết kiệm có kỳ hạn` được cộng
  theo đúng cột kỳ/tiền tệ vào ID 1063; các child VND/ngoại tệ vào 1064/1065.
- `Tiền gửi ký quỹ` đã map ID 1066; các child VND/ngoại tệ vào 1067/1068.
- Ba nhánh cấu trúc TSCĐ hữu hình 869/883/5964 không phải ba ô số độc lập. Giá
  trị được lấy ở cột `Tổng cộng` và map vào các child đầu kỳ, tăng/giảm, cuối kỳ
  bên dưới; cùng nguyên tắc cho TSCĐ vô hình và bất động sản đầu tư.
- Family TSCĐ thuê tài chính vẫn là 0 READY/140 NOT_OBSERVED: sáu chỗ có cụm từ
  này trong corpus đều là dòng balance sheet, không phải bảng tăng/giảm chi tiết.
- Phát hành giấy tờ có giá đã có mapping cho root ID 1100 ở 140/140 PDF cùng các
  leaf công cụ/kỳ hạn. Những dòng trục gộp hoặc contra còn SOURCE_ONLY là bằng
  chứng đối chiếu riêng, không có nghĩa toàn family chưa map.

## Toàn bộ 55 family

| # | Family | PDF | READY | NOT_OBSERVED | UNRESOLVED | SOURCE_ONLY trong PDF READY | Cấu trúc/biến thể chính |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Tiền, kim loại quý và đá quý | 140 | 72 | 68 | 0 | 0 | VND, ngoại tệ, vàng và tổng; một số ngân hàng tách chứng từ ngoại tệ hoặc kim loại quý khác. |
| 2 | Tiền gửi tại Ngân hàng Nhà nước | 140 | 71 | 69 | 0 | 0 | VND, ngoại tệ và tổng; đôi khi lồng theo quốc gia hoặc NHNN Việt Nam. |
| 3 | Tiền gửi tại và cho vay các TCTD khác — tài sản | 140 | 140 | 0 | 0 | 0 | Tiền gửi, cho vay, dự phòng và tổng; có cây tiền tệ/quốc gia và nhiều subtotal. |
| 4 | Chứng khoán kinh doanh | 140 | 111 | 29 | 0 | 0 | Chứng khoán nợ/vốn/khác và dự phòng; issuer view và niêm yết là hai cách trình bày. |
| 5 | Công cụ tài chính phái sinh | 140 | 126 | 14 | 0 | 0 | Giá trị dương/âm theo hợp đồng hoặc tiền tệ; MBB có header nhiều tầng. |
| 6 | Cho vay theo loại hình | 140 | 140 | 0 | 0 | 0 | Loại khoản vay, margin/ứng trước và tổng; bảng có thể có hai hoặc bốn lane tiền–tỷ lệ. |
| 7 | Cho vay theo ngành nghề kinh doanh | 140 | 98 | 42 | 0 | 0 | Danh mục ngành thay đổi theo ngân hàng; có nhãn gộp “Thương mại, dịch vụ”. |
| 8 | Chất lượng cho vay | 140 | 140 | 0 | 0 | 0 | Năm nhóm nợ và margin; VIB thường xếp kỳ dọc/nhiều cột tài sản. |
| 9 | Dư nợ theo thời gian/thời hạn gốc | 140 | 140 | 0 | 0 | 0 | Ngắn, trung, dài hạn và margin; HDB có population bổ sung dùng kiểm tra tổng. |
| 10 | Cho vay theo loại tiền tệ | 140 | 10 | 130 | 0 | 0 | VND và ngoại tệ/vàng; corpus hiện hành chỉ ACB và HDB trình bày đúng family. |
| 11 | Cho vay theo khu vực địa lý | 140 | 41 | 99 | 0 | 0 | Khu vực có thể nằm ở hàng hoặc cột; không nhận nhầm bảng địa lý population rộng hơn. |
| 12 | Cho vay theo loại hình doanh nghiệp/đối tượng | 140 | 84 | 56 | 0 | 0 | Doanh nghiệp theo pháp lý, cá nhân và nhóm khác; VCB có nhãn gộp, MBB có group parent. |
| 13 | Biến động dự phòng rủi ro cho vay | 140 | 140 | 0 | 0 | 0 | Đầu kỳ, trích lập, hoàn nhập/sử dụng và cuối kỳ theo từng lane; có bảng nhiều trang. |
| 14 | Hoạt động mua nợ | 140 | 64 | 76 | 0 | 0 | Giá mua, gốc, lãi, dự phòng và tổng; HDB có biến thể chỉ trình bày principal. |
| 15 | Tiền gửi khách hàng theo loại/kỳ hạn/đối tượng | 140 | 140 | 0 | 0 | 0 | Không kỳ hạn/có kỳ hạn, tổ chức/cá nhân, tiền tệ và tổng. |
| 16 | Chứng khoán đầu tư | 140 | 140 | 0 | 0 | 0 | Sẵn sàng để bán/giữ đến đáo hạn, nợ/vốn, dự phòng và chất lượng. |
| 17 | Các khoản đầu tư dài hạn khác | 140 | 140 | 0 | 0 | 0 | Công ty con/liên kết/liên doanh và đầu tư khác; giá gốc–dự phòng–giá trị còn lại. |
| 18 | Tăng, giảm TSCĐ hữu hình | 140 | 72 | 68 | 0 | 0 | Nguyên giá, khấu hao, tăng/giảm, giá trị còn lại; có bảng xoay và nhiều trang. |
| 19 | Tăng, giảm TSCĐ thuê tài chính | 140 | 0 | 140 | 0 | 0 | Đã quét đúng ranh giới note; không PDF nào có bảng chi tiết family này. |
| 20 | Tăng, giảm TSCĐ vô hình | 140 | 72 | 68 | 0 | 0 | Nguyên giá, khấu hao và giá trị còn lại; khác nhau ở phần mềm/quyền sử dụng đất. |
| 21 | Tăng, giảm bất động sản đầu tư | 140 | 12 | 128 | 0 | 0 | Nguyên giá, khấu hao, giá trị còn lại; ACB có hai bảng anh em cần ghép. |
| 22 | Tài sản Có khác | 140 | 78 | 62 | 0 | 304 dòng/67 PDF | Cây phải thu, chi phí chờ phân bổ, tài sản thuế và tài sản khác. |
| 23 | Nợ Chính phủ và Ngân hàng Nhà nước | 140 | 140 | 0 | 0 | 45 dòng/31 PDF | Tiền gửi/vay/tài trợ theo tiền tệ và chương trình; parent/subtotal được giữ riêng. |
| 24 | Vốn tài trợ, ủy thác đầu tư và cho vay chịu rủi ro | 140 | 76 | 64 | 0 | 12 dòng/4 PDF | Theo chương trình/dự án và tổng; tên dự án thường là chi tiết nguồn. |
| 25 | Phát hành giấy tờ có giá | 140 | 140 | 0 | 0 | 336 dòng/54 PDF | Trái phiếu/chứng chỉ tiền gửi theo kỳ hạn, mệnh giá, chiết khấu/phụ trội. |
| 26 | Các khoản phải trả và công nợ khác | 140 | 140 | 0 | 0 | 412 dòng/77 PDF | Lãi phải trả, thuế, nội bộ và phải trả khác; nhiều child nằm dưới parent đã map. |
| 27 | Vốn và các quỹ | 140 | 137 | 0 | 3 | 147 cột/91 PDF | Ma trận thành phần vốn × biến động đầu kỳ–tăng/giảm–cuối kỳ; BID/VIB có bảng xoay. |
| 28 | Thu nhập lãi và các khoản tương tự | 140 | 136 | 0 | 4 | 42 dòng/34 PDF | Tiền gửi, cho vay, chứng khoán, bảo lãnh, thuê tài chính, mua nợ và khác. |
| 29 | Chi phí lãi và các khoản tương tự | 140 | 140 | 0 | 0 | 32 dòng/32 PDF | Lãi tiền gửi, tiền vay, giấy tờ có giá và khác; root nguồn có thể chỉ là control. |
| 30 | Thu nhập từ lãi thuần | 8 | 8 | 0 | 0 | 0 | Dòng statement bằng thu nhập lãi trừ chi phí lãi; VIB đảo thứ tự nguồn. |
| 31 | Thu nhập, chi phí và lãi thuần dịch vụ | 140 | 68 | 72 | 0 | 51 dòng/10 PDF | Thu/chi/net theo dịch vụ; ACB tách hai note, CTG có nhãn gộp. |
| 32 | Lãi/lỗ thuần kinh doanh vàng và ngoại hối | 140 | 72 | 68 | 0 | 61 dòng/61 PDF | Thu, chi, chênh lệch và net; có nguồn gộp ngoại hối với vàng. |
| 33 | Lãi/lỗ thuần mua bán chứng khoán kinh doanh | 140 | 103 | 37 | 0 | 11 dòng/11 PDF | Thu, chi, dự phòng và net; không tự sinh 0 khi vai trò dự phòng vắng. |
| 34 | Lãi/lỗ thuần mua bán chứng khoán đầu tư | 140 | 112 | 28 | 0 | 62 dòng/26 PDF | Thu, chi, dự phòng và net; bảng gộp được giới hạn đúng subtree. |
| 35 | Lãi thuần chứng khoán kinh doanh và đầu tư gộp | 140 | 12 | 128 | 0 | 4 dòng/4 PDF | Chỉ map khi PDF in đúng dòng net gộp; không tự tổng hợp từ hai family khác. |
| 36 | Thu nhập góp vốn, mua cổ phần và cổ tức | 140 | 118 | 22 | 0 | 36 dòng/36 PDF | Cổ tức, vốn kinh doanh/đầu tư, dài hạn và equity method; không map lặp parent. |
| 37 | Chi phí quản lý chung/chi phí hoạt động | 140 | 138 | 0 | 2 | 284 dòng/108 PDF | Thuế phí, nhân viên, tài sản, quản lý, bảo hiểm, dự phòng và khác. |
| 38 | Chi phí dự phòng rủi ro tín dụng | 140 | 64 | 76 | 0 | 51 dòng/21 PDF | Trích lập/hoàn nhập theo loại rủi ro và tổng; có component chỉ dùng kiểm tra. |
| 39 | Thu nhập, chi phí và lãi thuần hoạt động khác | 140 | 72 | 68 | 0 | 0 | Thu, chi và net từ hoạt động khác; khép theo từng kỳ nguồn. |
| 40 | Chi phí thuế thu nhập doanh nghiệp | 140 | 69 | 71 | 0 | 282 dòng/69 PDF | Thuế hiện hành/hoãn lại và reconciliation; nhiều điều chỉnh chỉ phục vụ đối chiếu. |
| 41 | Tiền và các khoản tương đương tiền | 140 | 105 | 35 | 0 | 1 dòng/1 PDF | Tiền, tiền gửi ngắn hạn và khoản tương đương; owner không số được giữ cấu trúc. |
| 42 | Mua mới và thanh lý công ty con | 140 | 0 | 140 | 0 | 0 | Đã quét note và đối chứng âm; không có bảng giao dịch đủ điều kiện. |
| 43 | Thu nhập nhân viên ngân hàng | 140 | 60 | 74 | 6 | 0 | Số người, quỹ lương/thu nhập và bình quân tháng; MBB/VCB khác nhau về loại headcount. |
| 44 | Nghĩa vụ với ngân sách Nhà nước | 140 | 130 | 10 | 0 | 43 cột/20 PDF | Đầu kỳ, phát sinh, đã nộp, cuối kỳ theo sắc thuế; CTG có phải thu/phải trả. |
| 45 | Tài sản thế chấp của khách hàng ngân hàng đang nắm giữ | 140 | 58 | 82 | 0 | 25 dòng/20 PDF | Loại tài sản bảo đảm và tổng; owner/“Trong đó” chỉ dùng kiểm tra. |
| 46 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | 140 | 50 | 90 | 0 | 74 dòng/36 PDF | Theo tiền gửi, chứng khoán và repo; không ép tách nhãn “GTCG” gộp. |
| 47 | Nghĩa vụ nợ tiềm ẩn và các cam kết | 140 | 83 | 57 | 0 | 249 dòng/44 PDF | Bảo lãnh, L/C, hạn mức, swap, ký quỹ; nhiều “Trong đó” là control. |
| 48 | Công cụ tài chính — giá ghi sổ và giá trị hợp lý | 140 | 66 | 74 | 0 | 0 | Tài sản/nợ tài chính × giá ghi sổ/giá trị hợp lý. |
| 49 | Rủi ro tiền tệ | 140 | 140 | 0 | 0 | 0 | Tài sản, nợ, nội/ngoại bảng và trạng thái theo tiền tệ/vàng. |
| 50 | Rủi ro lãi suất | 140 | 139 | 1 | 0 | 0 | Tài sản/nợ theo bucket tái định giá; một PDF không có family. |
| 51 | Rủi ro thanh khoản | 140 | 138 | 2 | 0 | 0 | Tài sản/nợ theo bucket đáo hạn; cách gộp nội/ngoại bảng khác nhau. |
| 52 | Tỷ giá ngoại tệ cuối kỳ | 140 | 98 | 42 | 0 | 323 loại tiền/64 PDF | Mã tiền × tỷ giá hiện tại/so sánh; có XAU và nhiều mã hiếm. |
| 53 | Tiền gửi và vay các TCTD khác — nguồn vốn | 140 | 140 | 0 | 0 | 135 dòng/54 PDF | Tiền gửi/vay theo đối tác, tiền tệ, repo; IFC và UPAS L/C giữ đúng cấp. |
| 54 | Kinh doanh và đầu tư chứng khoán theo địa lý | 140 | 119 | 21 | 0 | 6 ô trống/6 PDF | Trong nước/nước ngoài hoặc quốc gia; ô trắng thật không đổi thành 0. |
| 55 | Báo cáo bộ phận hợp nhất | 140 | 45 | 95 | 0 | 1.149 dòng + 132 cột/39 PDF | Ma trận bộ phận kinh doanh/địa lý × sáu metric lõi; orientation khác mạnh giữa ngân hàng. |

## Family còn vướng

| Family | PDF UNRESOLVED | Vấn đề chính |
| --- | ---: | --- |
| Vốn và các quỹ | 3 | Có `Quỹ đầu tư phát triển` nhưng chưa có leaf schema đồng nhất; ma trận vốn chưa khép duy nhất. |
| Thu nhập nhân viên | 6 | Không xác định chắc headcount cuối kỳ hay headcount bình quân dùng làm mẫu số. |
| Thu nhập lãi | 4 | Dòng gộp khác bản chất schema, subtotal không nhãn hoặc số parent/child lệch. |
| Chi phí hoạt động | 2 | Một ô so sánh để trống; một PDF có token tiền lỗi và ba child chưa có leaf chính xác. |

Mở từng PDF và xem lý do chi tiết tại
[`UNRESOLVED_MAPPING_LEDGER_READABLE.md`](UNRESOLVED_MAPPING_LEDGER_READABLE.md#unresolved).
