# Family 21 – Tăng, giảm bất động sản đầu tư

## Kết luận kiểm tra nguồn

- Baseline 204 báo cáo: **3 READY / 199 NOT_OBSERVED / 2 UNRESOLVED**, 25 mapping.
- Corpus đầy đủ 271 báo cáo có đúng năm bảng tăng, giảm bất động sản đầu tư có số liệu: một bảng ABB, hai bảng SSB đã READY và hai bảng NAB bị thuật toán bỏ sót.
- Hai bảng NAB đều nhìn rõ trên PDF, đơn vị triệu đồng, chỉ có một cột tài sản `Nhà cửa, vật kiến trúc`. Nguồn không trình bày nhánh khấu hao vì toàn bộ giá trị còn lại bằng nguyên giá; đây là trường hợp nhánh khấu hao vắng mặt hợp lệ đã được khai báo trong evaluation policy.
- Replay cuối trên 271 PDF đạt **5 READY / 266 NOT_OBSERVED / 0 UNRESOLVED**, 38 mapping. Không còn trường hợp nhìn thấy đúng family mà bị giữ ở U/N do thiếu nhánh, header tương đối hoặc subtotal singleton.

## Hai bảng NAB phải được map

| Báo cáo | Trang PDF | Dòng nguồn | ReportNormId | Kiểm tra số học |
| --- | ---: | --- | ---: | --- |
| `vietstock_bctc/NAB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 50 | Nguyên giá đầu năm; thanh lý; nguyên giá cuối năm | 944; 952; 955 | 30.439 - 30.439 = 0 |
| Cùng báo cáo | 50 | Giá trị còn lại đầu năm; cuối năm | 5973; 5974 | 30.439 → 0, bằng nguyên giá vì không có hao mòn |
| `vietstock_bctc/NAB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 47 | Nguyên giá đầu kỳ; thanh lý; nguyên giá cuối kỳ | 944; 952; 955 | 30.439 - 8.885 = 21.554 |
| Cùng báo cáo | 47 | Giá trị còn lại đầu kỳ; cuối kỳ | 5973; 5974 | 30.439 → 21.554, bằng nguyên giá vì không có hao mòn |

Kiểm tra trực tiếp ảnh PDF xác nhận báo cáo năm tại trang PDF 10 có dòng gốc
`Bất động sản đầu tư`, giá trị `-` ở cột `Số cuối năm` và `30.439` ở cột
`Số đầu năm`; tiêu đề cùng trang ghi đầy đủ `tại ngày 31 tháng 12 năm 2025`.
Trang PDF 50 trình bày đúng bảng tăng, giảm: nguyên giá đầu năm `30.439`,
thanh lý/nhượng bán `(30.439)`, cuối năm `-`; giá trị còn lại đầu năm
`30.439`, cuối năm `-`. Vì vậy đây không phải lỗi nguồn, OCR hay thiếu schema.

Báo cáo sáu tháng tại trang PDF 47 cũng nhìn rõ nguyên giá `30.439 - 8.885 =
21.554` và giá trị còn lại `30.439 → 21.554`. Trường hợp này đã READY trên
engine trước sửa; chỉ báo cáo năm còn U vì bảng cân đối dùng header tương đối.

## Nguyên nhân thuật toán còn lại ở báo cáo năm NAB

Classifier control của bảng cân đối trước đây chỉ chấp nhận ngày đầy đủ ngay
trong từng header cột. Vì trang 10 dùng `Số cuối năm / Số đầu năm`, bảng gốc
hợp lệ bị rơi vào nhánh bảng không xác thực và chặn bảng thuyết minh trang 50
với các lý do kỹ thuật `CARRYING_SUMMARY_CONTROL_STRUCTURE_IS_NOT_AUTHENTICATED`
và `CARRYING_SUMMARY_CONTROL_POPULATION_IS_UNRESOLVED`.

Nhánh sửa generic chỉ được phép chạy khi đồng thời có đủ: section đã được gắn
kiểu `PRIMARY_STATEMENT / BALANCE_SHEET`; đúng một dòng gốc family; đúng hai cột
MONEY; tiêu đề/narrative section có duy nhất một ngày báo cáo đầy đủ; và hai
header khớp duy nhất vai trò cuối kỳ/đầu kỳ. Ngày cuối kỳ được lấy nguyên văn từ
tiêu đề section; cột đầu kỳ chỉ giữ vai trò tương đối và `period_date = null`,
không suy ngày 31/12 từ một năm đơn lẻ. Header trộn ngày cụ thể với vai trò tương
đối, thiếu ngày section, hai ngày section xung đột, trùng vai trò hoặc thừa cột
đều fail closed.

## Baseline false-positive phải loại

Baseline U còn lại là SSB `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025 - Nguồn chính thức SeABank.pdf`, trang 38. Visual PDF cho thấy đây là bảng **tài sản cố định hữu hình**, không phải bất động sản đầu tư; kết quả đúng là NOT_OBSERVED.

Replay 271 PDF trên engine trước sửa còn lộ thêm STB
`BCTC Hợp nhất Kiểm toán năm 2025.pdf`, trang PDF 54. Ảnh PDF cho thấy đây
là trang tiếp theo của **tài sản cố định vô hình**, với các cột `Quyền sử dụng
đất`, `Phần mềm máy vi tính`, `Khác`, `Tổng cộng`; trang không có owner bất
động sản đầu tư. JSON cũng ghi `continuation = CONTINUES_FROM_PREVIOUS_PAGE`
và đúng các cột trên. Vì biến thể `Phần mềm máy vi tính` chưa nằm trong
hard-negative F21, các dòng nguyên giá/hao mòn/giá trị còn lại dùng chung cấu
trúc đã tạo false U. Bổ sung alias biến thể này đưa tài liệu về NOT_OBSERVED;
không có khoản mục F21 nào bị bỏ.

## Sửa thuật toán và gate hồi quy

1. Khi `component_policy.optional_absent_branch_roles` khai báo `DEPRECIATION_BRANCH`, classifier phải xét frontier bắt buộc sau khi loại nhánh này; không được dừng sớm với `CONFIGURED_BRANCH_SEED_FRONTIER_INCOMPLETE`.
2. Chỉ cho phép thiếu nhánh khi các nhánh còn lại, owner, đơn vị, kỳ và phương trình đều xác thực. Không tạo mapping khấu hao bằng 0.
3. Một cột MONEY duy nhất đã khớp loại tài sản được dùng làm tổng ngầm định có receipt; nhiều cột thiếu `Tổng` vẫn bị từ chối.
4. Giá trị còn lại phải khớp chính xác với nguyên giá trừ hao mòn. Khi nhánh hao mòn vắng hợp lệ, giá trị còn lại phải bằng nguyên giá ở cả hai endpoint.
5. Full-corpus replay đã giữ nguyên ba READY hiện hữu, đưa đúng hai NAB sang READY, loại SSB tangible false-positive về N và không còn U.

## Subtotal tăng hao mòn khi PDF chỉ in một thành phần

Schema tách `Tổng tăng hao mòn bất động sản đầu tư trong kỳ` (ReportNormId
6005) và khoản mục con `Khấu hao trong kỳ` (ReportNormId 958). Một số PDF chỉ
in đúng một dòng tăng là `Khấu hao trong kỳ/năm`. Thuật toán hiện giữ mapping
958 từ ô nhìn thấy và đồng thời tạo mapping cha 6005 từ đúng cùng frontier,
nhưng chỉ khi: không có subtotal 6005 riêng; có đúng một dòng con được khai
báo; mọi cột tiền của dòng con đều hiện hữu; và phương trình biến động của cả
nhánh khép chính xác. Ô trống, nhiều parent có thể chọn hoặc phương trình lệch
đều không được suy subtotal.

| Ngân hàng | Báo cáo | Trang PDF | Dòng nhìn thấy | Mapping cha bổ sung |
| --- | --- | ---: | --- | ---: |
| ABB | `1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf` | 50 | Khấu hao trong kỳ: 623 triệu đồng | 6005 = 623 |
| SSB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | 39 | Khấu hao trong kỳ: 294 triệu đồng | 6005 = 294 |
| SSB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | 40 | Khấu hao trong kỳ: 587 triệu đồng | 6005 = 587 |

Hồi quy lịch sử cũng sửa đúng báo cáo
`MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf`, trang 61: dòng `Khấu hao
trong năm` có tổng 6.145 triệu đồng được map vào cả 958 và subtotal cha 6005.
Đây là chênh lệch duy nhất so với oracle trước khi sửa; sau sửa comparator đạt
16/16 tài liệu và 27/27 giá trị.

## Checkpoint terminal

- Full271: 5 READY / 266 NOT_OBSERVED / 0 UNRESOLVED; 38 mapping, 53 phương trình; hợp đồng quan sát nguồn đạt khi ingest.
- Strict old140: 12 READY / 128 NOT_OBSERVED / 0 UNRESOLVED; 110 mapping, 185 phương trình; comparator 16 tài liệu và 27 giá trị đều exact.
- 147 kiểm thử evaluator/indexed/runner đạt; negative bao gồm subtotal đã hiện hữu, ô con trống, phương trình nhánh không khép, cấu hình một child trỏ nhiều subtotal và pin mapping bị sửa giả.
- Artifact full271: `/dev/shm/family21-full271-singleton-final-v3.json` (SHA-256 `875fbcac7cfa29869e0d2770078e3dec7dfdeec26ded9bd03586619fadf2f2f3`).
- Artifact strict: `/dev/shm/family21-old140-strict-final-v3.json` (SHA-256 `30c6f80ccd2ae23acb810a56c2a3b79dc5cf55f199f64c0aeb3959a9274d9bb4`).
