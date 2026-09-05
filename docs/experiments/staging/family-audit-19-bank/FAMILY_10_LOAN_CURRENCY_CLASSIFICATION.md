# Family 10 — Phân tích dư nợ cho vay theo loại tiền tệ

Family 10 đã được chốt trên chỉ mục bất biến 271 PDF của 19 ngân hàng, gồm các báo cáo từ năm 2025 đến hiện tại. Kết quả cuối không còn `UNRESOLVED`; mọi bảng nhìn thấy trên PDF, đúng population và map được vào RNID 757/758 đều đã được xử lý bằng quy tắc tổng quát có receipt.

## Kết quả

### Tập 204 PDF ban đầu

| Trạng thái | Baseline đầu tiên | Checkpoint trước sửa cuối | Kết quả cuối |
|---|---:|---:|---:|
| READY | 16 | 50 | **55** |
| NOT_OBSERVED | 183 | 151 | **149** |
| UNRESOLVED | 5 | 3 | **0** |
| Mapping | — | 100 | **110** |

- So với baseline đầu tiên: 39 PDF chuyển sang READY, 34 false-N được loại và cả 5 U được giải quyết.
- So với checkpoint trước sửa cuối: đúng 2 N→R và 3 U→R; 50/50 READY cũ giữ nguyên tuyệt đối `status`, `mappings`, `candidate_count`, `selected_candidate_id` và `reasons`.
- Tổng cuối: **55 READY + 149 NOT_OBSERVED + 0 UNRESOLVED = 204 PDF**.

### Chỉ mục đầy đủ 271 PDF

| Trạng thái | Số PDF |
|---|---:|
| READY | **67** |
| NOT_OBSERVED | **204** |
| UNRESOLVED | **0** |
| Mapping | **134** |

67 PDF bổ sung đóng góp 12 READY và 55 true-N. Không có job sửa nguồn hoặc provider call trong replay này.

## Phân bố 271 PDF theo ngân hàng

| Ngân hàng | PDF | READY | NOT_OBSERVED | UNRESOLVED |
|---|---:|---:|---:|---:|
| ABB | 12 | 2 | 10 | 0 |
| BAB | 10 | 0 | 10 | 0 |
| BVB | 14 | 2 | 12 | 0 |
| EIB | 16 | 4 | 12 | 0 |
| KLB | 16 | 0 | 16 | 0 |
| LPB | 7 | 0 | 7 | 0 |
| MSB | 16 | 0 | 16 | 0 |
| NAB | 16 | 0 | 16 | 0 |
| NVB | 16 | 0 | 16 | 0 |
| OCB | 16 | 4 | 12 | 0 |
| PGB | 7 | 7 | 0 | 0 |
| SGB | 14 | 0 | 14 | 0 |
| SHB | 16 | 0 | 16 | 0 |
| SSB | 16 | 16 | 0 | 0 |
| STB | 16 | 9 | 7 | 0 |
| TCB | 16 | 0 | 16 | 0 |
| TPB | 16 | 4 | 12 | 0 |
| VAB | 15 | 11 | 4 | 0 |
| VBB | 16 | 8 | 8 | 0 |
| **Tổng** | **271** | **67** | **204** | **0** |

## Schema và quy tắc mapping

| Nội dung | ReportNormId | Chính sách |
|---|---:|---|
| Phân tích theo loại hình tiền tệ | 756 | Chỉ là owner/context, không phát sinh mapping giá trị |
| Cho vay bằng đồng Việt Nam | 757 | Map trực tiếp từ dòng VND |
| Cho vay bằng ngoại tệ và vàng | 758 | Map trực tiếp nếu nguồn gộp; cộng hai dòng ngoại tệ và vàng khi nguồn tách riêng và phép cộng khép kín |

Candidate chỉ được READY khi đồng thời thỏa owner đúng family, hai lane tiền hợp lệ, population là cho vay khách hàng, đơn vị/kỳ xác định được và tổng khép. Các bảng tiền gửi, cho vay TCTD khác, lãi suất hay rủi ro tiền tệ có cùng nhãn con vẫn bị hard-negative; không map dựa vào từ khóa ngắn.

## Hai false-N do owner nằm trong narrative

JSON của hai PDF trong tập 204 lưu câu owner ở `section.narratives_exact`, không nằm ở section/table title. Truy vấn cũ bỏ qua bề mặt này nên trả N dù bảng PDF đầy đủ. Quy tắc mới chỉ chấp nhận alias parent chính xác trong cùng section và lưu `parent_narrative_binding`; hard-negative trong narrative vẫn phủ quyết.

| Ngân hàng | File PDF | Trang | Bằng chứng | Kết quả |
|---|---|---:|---|---|
| ABB | `1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf` | 42 | Narrative `Phân tích dư nợ cho vay khách hàng theo tiền tệ như sau`, hai dòng VND/ngoại tệ và tổng khép | RNID757 = 112.947.019 / 96.811.407; RNID758 = 1.587.464 / 1.926.769 |
| OCB | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 44 | Cùng owner narrative; hai dòng và tổng khép, đơn vị VND | RNID757 = 185.466.846.882.146 / 170.134.777.810.018; RNID758 = 866.204.247.390 / 709.691.828.645 |

Một PDF bổ sung của OCB (`BCTC Công ty mẹ Kiểm toán năm 2025.pdf`, trang 43) có cùng cấu trúc và cũng được map đúng: RNID757 = 197.144.958.204.291 / 170.134.777.810.018; RNID758 = 1.619.987.622.519 / 709.691.828.645.

## Ba U nguồn lệch ±1 đã được xử lý có giới hạn

Ba bảng VAB đều nhìn thấy rõ trên PDF, đúng family, có đủ VND/ngoại tệ/vàng và chỉ lệch đúng một đơn vị hiển thị ở tổng hiện kỳ; lane so sánh khép chính xác. Đây là sai số làm tròn tại đơn vị trình bày, không phải thiếu dữ liệu. Chính sách chỉ cho phép residual tuyệt đối tối đa 1 ở phương trình tổng cuối, chỉ với hai lane MONEY; residual 2 vẫn bị từ chối.

| File PDF | Trang | Tổng cấu phần / tổng in | Receipt |
|---|---:|---|---|
| `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | 31 | 84.910.467 / 84.910.468 | `source_rounding_residual_coefficients=[1,0]` |
| `2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf` | 30–31 | 84.910.467 / 84.910.468 | Adjacent-page stitch + residual `[1,0]` |
| `BCTC Q1.2026 RIENG LE_0001.pdf` | 32 | 90.752.673 / 90.752.672 | `source_rounding_residual_coefficients=[-1,0]` |

Các dòng ngoại tệ và vàng riêng của VAB được giữ làm source provenance rồi cộng vào đúng một mapping RNID758; không sinh mapping trùng hoặc tự suy từ ô trống.

## Gate chống bỏ sót và false-N

- Đã xem trực tiếp contact sheet của toàn bộ 56 N trong 67 PDF bổ sung trước sửa; OCB annual là false-N duy nhất và đã chuyển READY. 55 trường hợp còn lại là true-N.
- Quét lại toàn bộ 204 N cuối trên frontier JSON đã xác thực: **0** section title, table title hoặc narrative còn khớp chính xác một parent alias Family 10.
- Các bảng còn có nhãn con kiểu VND/ngoại tệ đều nằm dưới owner hard-negative rõ ràng như tiền gửi, cho vay TCTD khác, lãi suất hoặc rủi ro tiền tệ; không phải bảng phân tích dư nợ cho vay khách hàng theo tiền tệ.
- Không có PDF nào có nội dung đúng schema nhưng bị giữ ở U/N do alias, owner, continuation, header, unit hoặc phép khép thuật toán.

## Kiểm thử và artifact

- Family/page-store suite: **54 passed**.
- Generic runner/flat replay suite: **71 passed**.
- Ruff: pass; `git diff --check`: pass.
- Full result: `/dev/shm/family10-full271-narrative-v1.json`, SHA256 `a3ae4cbe6538cf3da4a0759e9f3deff9f3498084940b3f0f806ad1746f5777fe`.
- Replay database: `/dev/shm/family10-full271-narrative-v1.sqlite3`, SHA256 `8e76fbf00cd78f3a99d4e40b2c87610f2c134fbf83a46abb44bc79211e718402`.
- Immutable corpus index: `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`.
- Visual evidence: `/dev/shm/f10-vab-visual.nMyQZG`, `/dev/shm/f10-narrative-visual.ep3raU`, `/dev/shm/f10-added-n-visual.rXoxBM`.
