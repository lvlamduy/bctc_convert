# Family 23 — Các khoản nợ Chính phủ và Ngân hàng Nhà nước

Checkpoint này chốt family trên corpus bất biến **271 PDF / 14.945 trang** của
19 ngân hàng, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Không gọi lại provider.

## Kết quả full-271

| PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED | Mapping | Phương trình |
|---:|---:|---:|---:|---:|---:|
| 271 | 269 | 2 | 0 | 1.158 | 427 |

| Ngân hàng | PDF | READY | NOT_OBSERVED | UNRESOLVED | Mapping |
|---|---:|---:|---:|---:|---:|
| ABB | 12 | 12 | 0 | 0 | 50 |
| BAB | 10 | 10 | 0 | 0 | 28 |
| BVB | 14 | 14 | 0 | 0 | 92 |
| EIB | 16 | 16 | 0 | 0 | 62 |
| KLB | 16 | 16 | 0 | 0 | 16 |
| LPB | 7 | 7 | 0 | 0 | 27 |
| MSB | 16 | 16 | 0 | 0 | 110 |
| NAB | 16 | 16 | 0 | 0 | 53 |
| NVB | 16 | 14 | 2 | 0 | 30 |
| OCB | 16 | 16 | 0 | 0 | 65 |
| PGB | 7 | 7 | 0 | 0 | 13 |
| SGB | 14 | 14 | 0 | 0 | 28 |
| SHB | 16 | 16 | 0 | 0 | 24 |
| SSB | 16 | 16 | 0 | 0 | 50 |
| STB | 16 | 16 | 0 | 0 | 109 |
| TCB | 16 | 16 | 0 | 0 | 56 |
| TPB | 16 | 16 | 0 | 0 | 92 |
| VAB | 15 | 15 | 0 | 0 | 153 |
| VBB | 16 | 16 | 0 | 0 | 100 |
| **Tổng** | **271** | **269** | **2** | **0** | **1.158** |

Hai `NOT_OBSERVED` và mọi candidate từng là `UNRESOLVED` đã được xem lại từ
ảnh PDF. Không còn nội dung nhìn thấy có thể map vào schema bị giữ ở trạng thái
`UNRESOLVED`.

## Hai PDF NOT_OBSERVED thật

| Ordinal | File PDF | Trang kiểm soát | Bằng chứng nguồn | Kết luận |
|---:|---|---:|---|---|
| 111 | [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf>) | 4 | Báo cáo tình hình tài chính chỉ in `Tiền gửi và vay các TCTD khác`, tách thành `Tiền gửi các TCTD khác` và `Vay các TCTD khác`; không có Chính phủ/NHNN. | Family không xuất hiện trong toàn bộ PDF; không được lấy family liên ngân hàng thay thế. |
| 114 | [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../../../vietstock_bctc/NVB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf>) | 4 | Cùng cấu trúc nguồn: chỉ `Tiền gửi và vay các TCTD khác`; không có dòng Chính phủ/NHNN. | `NOT_OBSERVED` là kết quả đúng. |

## SOURCE_ONLY còn lại — tám dòng không có leaf schema

Tám PDF TCB dưới đây đều `READY`: tổng `Vay Ngân hàng Nhà nước Việt Nam` đã
được map. Dòng con `- Bằng VND` là phân loại theo tiền tệ của khoản vay NHNN,
nhưng schema Family 23 không có leaf “vay NHNN bằng VND”. Nó không được map
nhầm sang `Tiền gửi Kho bạc bằng VND` và cũng không được nhân đôi vào parent.

| Ordinal | File PDF | Trang | Dòng nguồn |
|---:|---|---:|---|
| 209 | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 54 | `Vay Ngân hàng Nhà nước Việt Nam` → `- Bằng VND` |
| 214 | [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf>) | 43 | Như trên |
| 215 | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 63 | Như trên |
| 220 | [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../../../vietstock_bctc/TCB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf>) | 55 | Như trên |
| 221 | [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../../../vietstock_bctc/TCB/2026/BCTC Công ty mẹ quý 1 năm 2026.pdf>) | 42 | Như trên |
| 222 | [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../../../vietstock_bctc/TCB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf>) | 41 | Như trên |
| 223 | [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../../../vietstock_bctc/TCB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf>) | 52 | Như trên |
| 224 | [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../../../vietstock_bctc/TCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf>) | 52 | Như trên |

Đây là toàn bộ `source_only_unmapped_rows` trong artifact full-271: **8 dòng,
8 PDF**. Các dòng BAB `Vay chiết khấu các GTCG`, MSB `Vay thực hiện Dự án hiện
đại hóa Ngân hàng và Hệ thống thanh toán`, và các group STB `a Vay NHNN` / `b
Tiền gửi của KBNN` đã được map bằng alias đúng bản chất. STB ordinal 199 dùng
projection cấu trúc hẹp vì bảng công bố trực tiếp `Vay theo hồ sơ tín dụng` và
`Khác` dưới owner family mà bỏ carrier `Vay NHNN`; projection chỉ bổ sung cạnh
quan hệ, không tạo/chọn giá trị.

## Quy tắc recovery và hàng rào blank ≠ 0

- 42 PDF không có note chi tiết nhưng có đúng một dòng root Family 23 trên báo
  cáo tình hình tài chính được recovery bằng receipt exact. Receipt yêu cầu một
  alias root duy nhất, hai cột tiền có kỳ/đơn vị đầy đủ và không chọn hay hoàn
  thiện ô trống.
- Một continuation VAB ordinal 246 chỉ được nối từ trang 36 sang 37 khi owner
  kết thúc trang trước, fragment không title mở đầu trang kế, cùng source, hai
  trang vật lý liền nhau, kỳ/đơn vị tương thích và không có reset chen giữa.
  Mismatched-owner, non-adjacent và intervening-reset đều có negative test.
- Adapter loại mọi giá trị số bắt nguồn từ `source_text=null` và trạng thái suy
  blank. Một lane nhìn thấy vẫn được giữ; lane trống mang `coefficient=null` /
  `BLANK_SOURCE_CELL`. Không dùng phương trình để biến blank thành 0.
- 143 sửa chữa duy nhất đều là `null` → literal `-` khi PDF thật có dấu gạch
  ngang. Artifact đăng ký khóa SHA/size PDF, trang vật lý, SHA ảnh toàn trang
  300 DPI, SHA crop RGB, version JSON trang, section/table/row/column,
  `before_exact=null` và `after_exact="-"`. Thiếu, thừa, lặp hoặc drift bất kỳ
  byte/locator nào đều fail closed.

Artifact sửa nguồn có **143 ô trên 51 trang của 49 PDF**. SHA-256:
`12f17716792065eeeb1c0b09242da65d3b7ff8b2ab347434914c2c5b57000761`;
repair-axis SHA-256:
`ba793cb6e8e14b2701087944b140f649f477e81a9bad8801ffd43936dea6628f`.

## Replay và gate kỹ thuật

- Full-271 sweep:
  `gjfafsv1:sweep:c73f7857af0f6377d818bc0f5ae2e81a5e601e35490c72702794bfff5e6347a9`.
- Output SHA-256:
  `fdf64343695a56d92551bc20d62d01003584e5ae34ceb049d7b29ffe949a2df9`
  (48.972.446 byte).
- Ingest/source replay từ SQLite bất biến hoàn tất và trả đúng toàn bộ trial
  axis; family run:
  `gjfafstorev1:run:30e118ac0f8f2bd157946ae1dcef617ae216658cfa19b31b1a2e49a23127569d`.
- Global source-observation contract: **PASS**, 0 violation, 4.632 cell, 524
  derived cell, 14 partial mapping/14 blank source cell.
- Audit có 269 cluster, 1.158 mapping, 427 phương trình, 43 query recovery và
  143 source repair; mapping-axis SHA-256:
  `20a26ba29decba42d14d31d2cd4472fa6c58572bbfd4bd73e220ad4bd295617b`.
- Family, runner, source-observation và ingest-store suite: **38 test PASS**;
  Ruff, JSON parse và diff-check
  đều PASS.

## Differential common-204

Corpus common-204 giữ nguyên đúng thứ tự và SHA của 204 PDF baseline. Kết quả
đã ingest/source-replay thành công:

| Phiên bản | READY | NOT_OBSERVED | UNRESOLVED | Mapping |
|---|---:|---:|---:|---:|
| Baseline | 87 | 47 | 70 | 377 |
| Checkpoint này | 204 | 0 | 0 | 878 |

Cả 87 READY cũ vẫn READY; 47 NOT_OBSERVED và 70 UNRESOLVED đều chuyển READY,
không có chuyển trạng thái lùi. Tám dòng `- Bằng VND` của TCB vẫn được disclosure
SOURCE_ONLY vì cùng schema gap đã nêu, không làm mất các mapping chắc chắn.

- Sweep:
  `gjfafsv1:sweep:b78f38303401870e7d0990d86aac73918faa2b8ed03e92528ddef08d907d5d39`.
- Output SHA-256:
  `7942f765812d5a077d98f091e4abae3f5dd017f6b7fcf1f4414b08c7dbbcedd8`
  (37.550.181 byte).
- Family run:
  `gjfafstorev1:run:64e518f4923df6bc5ca1da17bd80d9e23beaaacedd54fe877e0fc9d6ca25c9ba`.
- Source-observation contract: **PASS**, 0 violation, 10 partial mapping/10
  blank source cell.

Replay full-271 độc lập lần hai tạo artifact byte-for-byte giống checkpoint
(`cmp` PASS), cùng sweep ID và SHA-256
`fdf64343695a56d92551bc20d62d01003584e5ae34ceb049d7b29ffe949a2df9`;
ingest/source-replay lần hai cũng `SUCCEEDED`, family run
`gjfafstorev1:run:5f1aeb8aa28e9f9b24f0bc8fe3f5acae6cc63a160f8583ae36ccbce859ef544a`.
