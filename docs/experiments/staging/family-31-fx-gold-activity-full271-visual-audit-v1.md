# Family 31 — kiểm toán hoạt động kinh doanh ngoại hối và vàng full271 v1

Ledger này ghi lại kiểm toán end-to-end Family 31 (`FX_GOLD_ACTIVITY`, RNID gốc
1175) trên corpus bất biến 2025–2026. Không gọi provider, không OCR lại để chọn
giá trị, không sửa shared evaluator/runner, và không coi kết quả thử nghiệm là
canonical hay export authority.

## Phạm vi nguồn đã xác thực

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422.971 byte, SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317.566 byte, SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
- Shared multitable evaluator được pin read-only tại SHA-256
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`.
- Shared generic runner được pin read-only tại SHA-256
  `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.
- Hai oracle lịch sử 8 ngân hàng có 16 source SHA hoàn toàn rời corpus hiện
  tại; runner dùng `DISJOINT_EXPANSION`, xác thực bytes/oracle axis nhưng không
  dùng chúng để kết luận cho full271/common204.

## Baseline và điều tra nguồn

Baseline trên chính shared bytes ở trên có 28 READY / 80 NOT_OBSERVED / 163
UNRESOLVED, 198 mappings. Artifact baseline
`/dev/shm/f31-baseline-bb319-v1/family31.json` có SHA-256
`f01b139a03c9340f92b741f7f8733d0601fba1fe2e20187500cd1c1784de5ef6`.
Các cohort lớn là 110 hàng nguồn top-level chưa khai báo validation role, 16
hàng tiền trực tiếp chưa map, 40 trường hợp thiếu một hoặc cả hai parent, tám
fragment thiếu period/unit cục bộ, và tám source root chưa được chứng minh.

Quét toàn bộ 14.945 selected pages cho thấy 451 bảng có bề mặt Family-31, 441
bảng nằm trong target context. Census bất biến ở
`/dev/shm/f31-current-selected-source-table-census-v1.json` (2.407.721 byte,
SHA-256 `d14b33de20a1d40d1a62fa89e15b3730bc13218f44e275f0f413255e9fd55604`).
Mọi alias mới đều xuất phát từ các bề mặt này; không có nhánh theo ngân hàng,
tên file, ordinal, page, note number hay giá trị.

## Biên adapter family-local

Shared evaluator tiếp tục chịu trách nhiệm phân loại bảng, period/unit axis,
source arithmetic, mapping và closure. Adapter Family-31 chỉ thực hiện các
biến đổi clone-only, có receipt và replay xác định:

1. Chọn đúng một hàng root hiển thị trên `INCOME_STATEMENT` khi không có note
   candidate trực tiếp; giữ nguyên hàng, cột, raw value và source locator.
2. Cho phép unitless note dùng unit statement chỉ khi exact root vector khóa
   duy nhất một unit; local unit hoặc xung đột vẫn thắng/veto. Không dùng độ
   lớn số, khoảng cách trang hay scale inference.
3. Ghép continuation chỉ khi marker hai chiều, thứ tự trang và period axis
   đều exact; conflict, đảo lane, không liền kề hoặc nhiều predecessor fail
   closed.
4. Khôi phục các subtotal/root không nhãn chỉ khi cấu trúc, source order và
   tất cả phương trình trực tiếp khép trên mọi lane. Source refs được trả về
   hàng PDF/JSON gốc, không giữ locator của hàng projected.
5. Thay root generic-derived bằng root source-visible chỉ khi đúng một hướng
   dấu của hai parent khớp source root. Không backsolve hoặc đổi dấu child.
6. Role gộp “spot FX + revaluation” chỉ là validation-only; không tách một
   hàng nguồn thành hai RNID giả.

Mọi candidate và indexed-query adaptation được dựng lại từ selected page JSON
trong `validate_*_replay_v1`. Store callback cũng query, adapt và evaluate lại
từ snapshot SQLite, không nhận expected trial làm đầu vào.

## Sửa nguồn PDF có xác thực

Registry
`data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json` chứa bốn
repair trên bốn PDF, tổng cộng bảy ô. Tất cả đều là dấu `-` nhìn thấy trực tiếp
trên PDF nhưng selected JSON lưu `null`:

| Nguồn | Trang vật lý | Ô sửa | Kết luận trực quan |
|---|---:|---:|---|
| SGB Q1/2026 hợp nhất | 34 | 4 | Hai dấu ở expense parent/spot comparative và hai dấu derivatives |
| SSB kiểm toán công ty mẹ 2025 | 52 | 1 | Expense-gold current in dấu `-` |
| SSB công ty mẹ Q4/2025 | 48 | 1 | Expense-gold current in dấu `-` |
| STB kiểm toán công ty mẹ 2025 | 67 | 1 | Income revaluation comparative in dấu `-` |

Mỗi repair bind source PDF SHA/size, selected page JSON SHA, full page RGB
300-dpi SHA, table crop RGB SHA, cell crop RGB SHA, row hierarchy, header path,
table/row/column và before-image. Compiler, apply và replay đều fail closed khi
bất kỳ byte/locator/crop nào lệch. Review policy là
`TRANSCRIBE_ONLY_AUTHENTICATED_PDF_VISIBLE_DASH_NO_EQUATION_BACKSOLVE_NO_BLANK_TO_ZERO_NO_PROVIDER`.
Các crop bảng đã được xem lại thủ công ngày 2026-09-04; cả bảy glyph đều rõ.

## Null, dấu gạch và phương trình

- Dấu `-` hiển thị là `DASH_ZERO` có source observation.
- Ô trống thật giữ `null`/`BLANK_SOURCE_CELL`; không bao giờ bị đổi thành 0.
- Full271 có 26 mapping partial (52 occurrences trong candidate + trial audit).
- Không phương trình nào được dùng để tạo một child value vắng nguồn.
- Parent label-only chỉ được map khi subtotal in trực tiếp hoặc direct-child
  frontier exact; state/cell receipt phân biệt rõ source và derived group.

Full271 có 594 phương trình: 267 hierarchy direct-child, 130 signed source-root,
61 top-level printed-total frontier, 61 unique root-sign, 42 contiguous
direct-role frontier, 30 label-only proxy, hai ordered-prefix subtotal và một
all-preceding total. Mọi phương trình đều có lane status/source refs.

## Gate không bỏ sót hàng nguồn

Runner duyệt mọi MONEY row trong mọi bảng target-like, kể cả hàng không map.
Full271 bind 16.313 hàng với đúng một disposition:

| Disposition | Số hàng |
|---|---:|
| Direct mapping source | 1.326 |
| Selected exact proof source | 249 |
| Selected validation-only source | 32 |
| All-blank structural group non-observation | 32 |
| Sau structural reset kết thúc F31 | 29 |
| Ngoài selected F31 owner fence | 1.665 |
| Primary-statement alternate source result | 11.182 |
| Typed control ngoài F31 | 1.798 |

Coverage receipt `f31srcrowv1:receipt:6f447f48f8541715a6b914c885b518621dd93216e9394d3b27c48da8fdc5c21b`
có row-axis SHA-256
`994eb270aff2c702a5f643bd68556188d6a42a655da232ef34715ab1bc60ad05`
và zero violation. Receipt hiểu cả canonical `before_locator` của projection,
nên 26 subtotal/root không nhãn ở KLB/SSB không bị báo giả là bỏ sót.

## Kiểm tra mọi primary presentation

Có 282 primary Family-31 presentations trong 271 tài liệu: 258 cùng vector và
unit với graph được chọn, 13 cùng vector nhưng primary row không có local unit,
bảy VAB trình bày VND nằm đúng khoảng hiển thị của mapping triệu đồng, và bốn
VAB thật sự lệch ít nhất một lane. Hai cohort VAB cuối chỉ được ghi nhận để
audit, không dùng để route, chọn representation, scale hay sửa mapping.

Receipt `f31prpav1:receipt:f2c8268ac555bb13bb8cbcc0f23069502641cfa121da5de687cedf4f2a404858`
có presentation-axis SHA-256
`aec896f981c77ea999edb6b2a15d4758e46a2067ab898e83675584e2bfc2a836`
và zero violation.

## Kết quả terminal

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings | Equations |
|---|---:|---:|---:|---:|---:|---:|
| full271 | 271 | 271 | 0 | 0 | 1.446 | 594 |
| common204 | 204 | 204 | 0 | 0 | 1.091 | 442 |

Full271 mapping role census: root 271; income/expense parent 191/191; spot FX
143/140; currency derivatives 189/179; gold 42/35; combined spot-FX-and-gold
31/32; other 1/1. Unit census là 1.376 `MILLION_VND` và 70 `VND`.
Toàn bộ 271 root mappings đều source-visible: 130 được unique signed-component
equation xác nhận, 80 là exact primary root-only row, 61 là printed total được
direct frontier chứng minh.

Source-observation full271 PASS: 2.892 nested mapping occurrences, 5.784 cells,
52 partial occurrences, 52 source-blank cells, 96 derived cells, zero
violation.

Common204 mapping role census: root 204; income/expense parent 142/142; spot FX
111/108; currency derivatives 141/134; gold 32/29; combined
spot-FX-and-gold 23/23; other 1/1. Unit census là 1.038 `MILLION_VND` và 53
`VND`. Root state census là 97 signed-source roots, 62 exact primary root-only
rows và 45 printed totals được direct frontier chứng minh. Có 18 mapping
partial duy nhất; source-observation audit đếm 2.182 nested occurrences, 4.364
cells, 36 partial/source-blank occurrences, 72 derived cells và zero violation.

Common204 source-row gate bind 12.340 hàng, gồm 999 mapping sources, 191 exact
proof sources, 16 validation-only sources, 25 all-blank groups, 29 rows sau
structural reset, 1.103 ngoài owner fence, 8.521 primary alternates và 1.456
typed controls; zero violation. Primary audit có 214 presentations: 193 exact
same-unit/vector, 11 exact vector không local unit, bảy VAB trong khoảng hiển
thị và ba VAB lệch thật sự.

## Artifact và store

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `/dev/shm/f31-bb319-full271-final-v2/family31.json` | 52.132.893 | `612c74f64f908f7f8617b0d0efea9ab68c57c57462aff863ca2c1ed7ab9c607a` |
| `/dev/shm/f31-bb319-full271-final-v2/family31.audit.json` | 13.756.668 | `011a8617a4327dda74dc2df27fe8186d7ee853ced1c8652c005b99d98b843b6c` |
| `/dev/shm/f31-bb319-full271-final-v2/results.sqlite3` | 88.702.976 | `1668335b4fb7fd661a2e6f314e539cad382d57a3ce341259da1805b091c383b5` |
| `/dev/shm/f31-bb319-common204-final-v1/family31.json` | 39.675.812 | `fb5053036c584fc1dac8d11ed9ba3a2a26de8b30447463d66ac05594f17e46c0` |
| `/dev/shm/f31-bb319-common204-final-v1/family31.audit.json` | 10.428.129 | `681107b088c1531156ea54e0e33a82ad83be0a51d87944d892a7fcdb762cdcdd` |
| `/dev/shm/f31-bb319-common204-final-v1/results.sqlite3` | 67.301.376 | `ea2cfb64638a79cfcf67735f0f69ccd7996c184f7a2f92112046003f97541bc9` |

Full271 IDs: sweep
`gjfafsv1:sweep:e902a5f8fc6d6df7b7ef9aa04f439c813abfec542c289b2d93cb2dc5c7830470`,
audit
`gjfgaauditv1:audit:be437f534261af0d56fdefbd7a039260bb9c65846ced9138b90be37ae549e68b`,
store run
`gjfafstorev1:run:db488414f455227c9a1c76ff47c6bf86f77464edced82a818fa637d81173e3db`.
SQLite trả `quick_check=ok`, `integrity_check=ok`, foreign-key check rỗng.
Common204 IDs: sweep
`gjfafsv1:sweep:cc7857070429677cf7b707b333be52a05e41d16f401565bddc3b3663d311ab6d`,
audit
`gjfgaauditv1:audit:1ef8ce9a1a8f8bab13a17ca98c6ef14d44a0a61fa2db57703f62da7b0bac6146`,
store run
`gjfafstorev1:run:aebb3b2f7c9e4a3bae30a3473c25b0e42ad276e7d50448ec277b7ea7874c4a2e`.
SQLite common204 cũng trả `quick_check=ok`, `integrity_check=ok` và foreign-key
check rỗng.

## Common/full semantic projection

Common204 là exact source-SHA subset của full271; full271 có đúng 67 nguồn bổ
sung. Receipt bất biến
`/dev/shm/f31-bb319-common204-full271-semantic-projection-receipt-v1.json`
(20.584 byte, SHA-256
`ea2db4ffc47c610d057236e01c9f2f2b6b0ff668753d1f6fe6d8405d12d12c8b`)
có ID
`f31cfsprv1:receipt:18e5dc79f6f3bf2e99e04dfe1e7572f352ac7eb93fd5713b0e8d428561b14d7a`.

Gate dùng `source_sha256` làm khóa và loại chỉ các identity phụ thuộc corpus
(document ID/ordinal, fragment/selected-page ordinal và các content-derived
candidate/mapping/equation/receipt IDs). Nó vẫn giữ status, reasons, RNID,
role, row ID, state, unit, typed coefficient/source text/state, hierarchy,
label, `page_json_version_id`, trang vật lý, section/table/row và money-column
ordinals. Kết quả là 0/204 mismatch; hai projected axes có cùng SHA-256
`68df002bba1789f25b8d92fdf1605930ae0b59d0ccb5a36b407fb0d6c91b0bbc`.
Source axis 204 có SHA-256
`a36b8489aa5f104c8d2ffe312893f4ce5c4d4c40a38b32ccb836b50dddf0ff7a`;
67-source expansion axis có SHA-256
`d11601e605ee26c2ae0d47206e2b64af75b3da338f3b8dfdd212f9c55f127c88`.

## Hash family-local và kiểm thử

| Path | SHA-256 |
|---|---|
| `config/families/tm-fx-gold-activity-topology-v1.json` | `a89c2624eae6479785663c361b79bde69ffcd203652978ecac1c8b27f835e11b` |
| `config/families/tm-fx-gold-activity-evaluation-v1.json` | `f3698ef682d14b18017683cc8f149037b2596a4d3b3afa13938cc587e5c72436` |
| `config/families/tm-fx-gold-activity-schema-binding-v1.json` | `5738b2f9a7c3219e2d714ab61c01723ebfdd4dd31bf332bbc07f664646bf2db8` |
| `data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json` | `d02aaff2a56a721df450d4ff5f81f249774e0d65a0fc07f0aa38d48d00c17805` |
| `src/bctc_ai/evaluation/gemini_json_fx_gold_activity_family_v1.py` | `dc54d8561d6e01e3c49130b84022343508e2bcd541d703a49490481f02a1f4c4` |
| `scripts/experiments/run_gemini_json_fx_gold_activity_accounting_family_v1.py` | `84d7bdbe29dfd30220825c04fd15f3e8502627c5a610c7f4619f1aba6a13105a` |
| `tests/unit/test_gemini_json_fx_gold_activity_family_v1.py` | `34d4de1753807d647183e86957fd61403a77f4c699820d8aa094ed73b63bc951` |
| `tests/unit/test_run_gemini_json_fx_gold_activity_accounting_family_v1.py` | `de6b9dd496b4447f1271789c84ea0123638daf5584c04f03e885271b6bf30f14` |

Family + runner + global source-observation targeted gate có 97 tests PASS;
family subset riêng có 89 PASS. `py_compile`, Ruff và `git diff --check` đều
PASS. Cả full271/common204 đều đã source replay từ SQLite, load lại typed-equal
với sweep trước ingest và ghi export receipt thành công.
