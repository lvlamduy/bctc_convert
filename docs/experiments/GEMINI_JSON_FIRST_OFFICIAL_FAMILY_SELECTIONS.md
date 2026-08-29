# Gemini JSON-first official family selections

Đây là checkpoint machine-derived của pipeline Gemini JSON-first mới. Nó không
thay thế các hồ sơ lịch sử trong `COMPLETED_TM_FAMILIES.md` và không cấp quyền
cho PP-OCR, VietOCR hoặc geometry quay lại đường production.

## Authority

- Corpus index:
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-corpus-manifest-indexes/61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3.json`
- Family result database:
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family-results.sqlite3`
- Corpus: 140 tài liệu, 8.947 page JSON đã chọn.
- Bảng có thẩm quyền hiện tại: `family_current_selection`; một run chỉ được
  ghi vào đây sau khi chạy lại với `run_kind=OFFICIAL`.
- Checkpoint source cho Family 4 và matcher chuẩn hóa:
  `24d0cbd` (`Resolve bounded Gemini family title variants`).

## Current sequential axis

| Family | Family ID | READY | NOT OBSERVED | UNRESOLVED | Mappings | Current run |
|---:|---|---:|---:|---:|---:|---|
| 1 | `CASH_PRECIOUS_METALS` | 72 | 68 | 0 | 292 | `gjfafstorev1:run:fe78eead6fe22711af891c785b1a53a21f73f31fe7fcba67ad23cdb90b6fb245` |
| 2 | `CENTRAL_BANK_DEPOSITS` | 71 | 69 | 0 | 249 | `gjfafstorev1:run:c41e3948f6c3327e7d5252f372a07e286bc174ebf4cb22294378bbc084fef177` |
| 3 | `INTERBANK_DEPOSITS_AND_LOANS` | 140 | 0 | 0 | 895 | `gjfafstorev1:run:a813e18dfed2631f641e303911fe102071471f94cf3580b237dfb2fa351b76fb` |
| 4 | `TRADING_SECURITIES` | 111 | 29 | 0 | 606 | `gjfafstorev1:run:f89afd5b63eac00cad13407126733b979c7fa42e08e689e4fba2bd3b58e16eac` |
| 5 | `DERIVATIVE_FINANCIAL_INSTRUMENTS` | 126 | 14 | 0 | 2.035 | `gjfafstorev1:run:26a88538b6e2150081342f7ac7b9cbf12e0893f7a50e259b254314b31ffde2b2` |
| 6 | `LOAN_TYPE_CLASSIFICATION` | 140 | 0 | 0 | 861 | `gjfafstorev1:run:44d54904bab4d0a5aefdf9cb42c7804dd53b9e87bf34b0453024b143e4fd923d` |
| 7 | `LOAN_INDUSTRY_CLASSIFICATION` | 98 | 42 | 0 | 1.618 | `gjfafstorev1:run:c48c3c9d742a15bba9a04b3ad0c2805ba219845ff5b4435cdc6daacefdcbb724` |
| 8 | `LOAN_QUALITY_CLASSIFICATION` | 140 | 0 | 0 | 867 | `gjfafstorev1:run:49b58fd099a2a7e45e145f0485def1736a472f12e415af7d78166e6f38ad41d3` |
| 9 | `LOAN_MATURITY_BUCKETS` | 140 | 0 | 0 | 438 | `gjfafstorev1:run:fddb4e5c2e7ee969d20c226edd2eca640fdd001ee27f0cfd09c03d6f962f80d1` |
| 10 | `LOAN_CURRENCY_CLASSIFICATION` | 10 | 130 | 0 | 20 | `gjfafstorev1:run:9cfa45e2a2dbc6da2e8227e6b7baf6ce09a5b6b0955b83e580ac3145221cd8b5` |
| 11 | `LOAN_GEOGRAPHIC_CLASSIFICATION` | 41 | 99 | 0 | 82 | `gjfafstorev1:run:a2723ed4c4b6108ab66bffd5d19006eca1abf7cb31ec3895d09a392d3ace62f7` |
| 12 | `LOAN_ENTERPRISE_FAMILY12` | 84 | 56 | 0 | 903 | `gjfafstorev1:run:4d953adc4d8fd66f85b612488ee5f7225db1cfa2f4bb48853d993e040c90fb98` |
| 13 | `PROVISION_MOVEMENT_ROLLFORWARD` | 140 | 0 | 0 | 1.281 | `gjfafstorev1:run:f682b2a8a0387028620afdf85d9f06d7b1720818a078a00803d8e4f09968ff73` |
| 14 | `PURCHASED_DEBT_ACTIVITY` | 64 | 76 | 0 | 254 | `gjfafstorev1:run:661c164d6298807f8030cf33ab6772145586360f815aaa6b29aeddbb5c102210` |
| 15 | `CUSTOMER_DEPOSIT_CLASSIFICATION` | 140 | 0 | 0 | 2.206 | `gjfafstorev1:run:db06abbffa2072b6988c06c6878549a4fff2467ff9751bd55f62f567d966b838` |
| 16 | `INVESTMENT_SECURITIES` | 140 | 0 | 0 | 2.149 | `gjfafstorev1:run:e53706dab2ac9695d30524070b4568223c99a78fd7a83d9af7d1d65c1b7ba1e1` |
| 17 | `OTHER_LONG_TERM_INVESTMENTS` | 140 | 0 | 0 | 429 | `gjfafstorev1:run:c7b8dba996e04c3f70468c54ca0104937360ae09c1ffa6e89f5a3faec71c203b` |
| 18 | `TANGIBLE_FIXED_ASSETS_ROLLFORWARD` | 72 | 68 | 0 | 875 | `gjfafstorev1:run:72c996032c969c655a69d28d2a1fcf213c0d264b658c3fed72d1e7300656c92f` |
| 19 | `LEASED_FIXED_ASSETS_ROLLFORWARD` | 0 | 140 | 0 | 0 | `gjfafstorev1:run:d7172f4b3b197e96be5a3b6c58543de7d69c5b5bdc76703cfa427ed2b12d11bc` |
| 20 | `INTANGIBLE_FIXED_ASSETS_ROLLFORWARD` | 72 | 68 | 0 | 829 | `gjfafstorev1:run:9bfd9b098cf14d5c7d39e356e5c2626ac2b964d32fe1e22da9ea7de3dbb8072c` |
| 21 | `INVESTMENT_PROPERTY_ROLLFORWARD` | 12 | 128 | 0 | 105 | `gjfafstorev1:run:b06b23729d51a3282e419de7e607ba394f4b85d2650f925fc808821256396ba1` |
| 22 | `OTHER_ASSETS` | 78 | 62 | 0 | 1.290 | `gjfafstorev1:run:a405aebffe52ca4a61ece9a918d6ba9af8cab81e34b626ab5278461252b5b531` |
| 23 | `GOVERNMENT_SBV_LIABILITIES` | 140 | 0 | 0 | 739 | `gjfafstorev1:run:96f56c6a071bd4dca415411ea8073f52e80dace6628d7c59f5295e7a18356dbf` |
| 24 | `ENTRUSTED_INVESTMENT_RISK_CAPITAL` | 76 | 64 | 0 | 174 | `gjfafstorev1:run:c863cc895b37c038a18bdf1d013f60626394c0256f66efb96dcd5b3be4980351` |

Tại checkpoint này database có đủ đúng hai mươi bốn current selection liên tục
từ Family 1 đến Family 24. Family 25 chưa được promote và không được bỏ qua.

## Family 4 closure

Artifact OFFICIAL:
`/tmp/gemini-json-family4-official-24d0cbd.json`, SHA-256
`509d3eea4ac1b0543012012609acfe3ca95c9d583ed196e3b847423cb3cba4a5`,
1.197.474 byte, sweep
`gjfafsv1:sweep:e8ee2ca95c05675c18cc8debe833e3576d0cb06388e7e6ba5b62688c45472ff6`.

- CTG ordinal 46 có source title `CHỨNG KHOÁN KINH DOAN`. Một ký tự thiếu chỉ
  tạo parent proposal; candidate chỉ READY sau khi một cây trực tiếp duy nhất,
  exhaustive và phương trình tất cả money lane đều khép chính xác.
- VPB ordinal 124 là continuation của `CHỨNG KHOÁN ĐẦU TƯ`, không phải
  `CHỨNG KHOÁN KINH DOAN`; receipt bind trang generic continuation với đúng
  một tiêu đề hard-negative continuation ở trang kề bên, nên disposition là
  NOT OBSERVED và mappings rỗng.
- So với run ngay trước sửa, 110/110 mapping arrays đã READY giữ nguyên
  canonical bytes. Chỉ ordinal 46 chuyển U→READY và ordinal 124 chuyển
  U→NOT OBSERVED.
- Audit độc lập: 98/98 test, Ruff, format và diff-check xanh; production diff
  không có bank/path/page/value routing.

## Normalized semantic matching policy

Mỗi label vẫn giữ `label_exact`. Truy vấn và matching có thêm dạng lowercase,
không dấu, whitespace/punctuation-normalized và ordered core phrases. Một cụm
nghĩa lõi đặc trưng có thể nằm trong tên dài hơn, nhưng các từ chung riêng lẻ
không đủ thẩm quyền. Nếu hai anchor chưa tạo vùng duy nhất thì tăng lên ba;
READY còn phải được corroborate bởi parent/child/sibling/order/context và
accounting graph. Fuzzy one-character match chỉ là proposal và không thể tự
phát mapping.

## Family 9 closure

Artifact OFFICIAL:
`/tmp/gemini-json-family9-official-bcd1d1d.json`, SHA-256
`80b46c1516aadcdef23c4731cdf3eb08caa4ca28d3db29898bb2d882a648ef89`,
770.264 byte, sweep
`gjfafsv1:sweep:0e266152006a98ecb3729364086a01fba1c926a6eb6078d64a475933cc39c29f`.

- Kết quả: `READY=140`, `UNRESOLVED=0`, `NOT_OBSERVED=0`, 438 mappings và
  không tạo repair job.
- Raw punctuation aliases chỉ dùng cho indexed shortlist; semantic matching
  vẫn dùng normalized roles và near-path chỉ đọc đúng required child roles.
- Header `12/31/2024` chỉ được đọc MDY vì cách DMY bất khả thi; ngày mơ hồ vẫn
  giữ DMY authority.
- RNID 752 là context-only: root equation vẫn bắt buộc khép nhưng chỉ phát
  753/754/755 và optional 5747.
- Đối chiếu độc lập với formal cũ: 140/140 source, 438/438 vectors, 876/876
  cells, không thiếu/thừa, không lệch value hay period. Fingerprint vector là
  `f13d3a61addc97be1d341c5cffd2005b890851ee634dc8050aecb50a27b631c4`.
- Gate code tại `bcd1d1d`: 103/103 test, Ruff/format xanh; Family 4 control
  giữ nguyên 140/140 status, mappings và reasons.

## Family 10 closure

Artifact OFFICIAL:
`/tmp/gemini-json-family10-official-8a225db.json`, SHA-256
`79a849d8c8ab9e589f2d03be9f76e401382efa4f8827d6c193d2c3327f4b4423`,
97.879 byte, sweep
`gjfafsv1:sweep:2d11616ce7f27a3e46a2882f4dd7b8c2d8e6172936ef1bfcf0712668bb64cc63`.

- Kết quả: `READY=10`, `NOT_OBSERVED=130`, `UNRESOLVED=0`, 20 mappings và
  không tạo repair job.
- RNID 756 là context-only; chỉ RNID 757/758 được phát. Sáu hồ sơ ACB dùng
  cặp nhãn đầy đủ, bốn hồ sơ HDB dùng owner `Cho vay khách hàng` với cặp nhãn
  ngắn được bind theo đúng scope.
- Query tách hai mode: cặp nhãn đầy đủ, hoặc owner cấu trúc cộng cặp nhãn
  scoped. Vì vậy `Bằng VND`/`Bằng ngoại tệ` trong bảng rủi ro tiền tệ không
  trở thành family candidate.
- Ba phương trình exhaustive dùng chung cho core, thư tín dụng trả chậm và
  family root; các dòng thư tín dụng chỉ corroborate closure, không được map.
- Đối chiếu formal cũ: 20/20 vectors, 40/40 cells và tổng hệ số
  11.489.059.821 bằng tuyệt đối. Fingerprint vector là
  `f4c12ce95f175804194e41b92644c5334ce02d672e7e85935dbfde788ee492ad`.
- Gate tích hợp tại `8a225db`: 116/116 test tác động xanh; replay Family 9 giữ
  nguyên artifact SHA-256 `80b46c...ef89`. Family 4 giữ nguyên output của
  baseline `bcd1d1d`; khác biệt với artifact OFFICIAL cũ là runner evolution
  có trước Family 10, không phải thay đổi query này.

## Family 11 closure

Artifact OFFICIAL:
`/tmp/gemini-family11-official-f95e367.json`, SHA-256
`643a5e01de48e50ec5a4efe8a6548695ecf342da18328e4cca1e68adf2e0352b`,
1.155.468 byte, sweep
`gjfafsv1:sweep:5aa7b8a3d241f067a8d3ccfb47103c8ce7ef46086408c5b41bad4e063b45f095`.

- Kết quả: `READY=41`, `NOT_OBSERVED=99`, `UNRESOLVED=0`, 82 mappings,
  142 cells, 71 phương trình và không tạo repair job.
- RNID 716/759 chỉ là context; chỉ RNID 5752 `DOMESTIC_TOTAL` và RNID 765
  `FOREIGN_TOTAL` được phát.
- Shared dual-axis engine xử lý cả hai layout: geography ở hàng với metric ở
  cột, hoặc metric ở hàng với geography ở cột; một hoặc hai bảng kỳ trên cùng
  hay hai trang kề nhau đều dùng cùng primitive.
- Query indexed thu hẹp 564 row hits xuống 341 candidate tables trước khi chỉ
  decode 1.323 column headers; frontier cuối có đúng 71 tables/59 pages/41
  documents. Region-axis SHA-256 là
  `5cbd1a057f122df908b5afddb8c632f0785f398f669dd1da86901b59069963c8`.
- 32 ô dash giữ nguyên evidence. Chỉ 16 ô `FOREIGN_TOTAL` trống được suy ra 0,
  và chỉ khi phương trình nguồn hiển thị chứng minh chính xác
  `TOTAL = DOMESTIC_TOTAL`; không cho phép suy ngược số khác 0 hoặc suy ô
  `DOMESTIC_TOTAL` trống.
- Đối chiếu độc lập giữ nguyên 76/76 mappings lịch sử và thêm đúng sáu mappings
  từ ba hồ sơ ACB trước đây chưa quan sát. Fingerprint đầy đủ là
  `911d886708b25b0ab5c64de852b8f4499077e8feded3b6baacccd62ab3e76d0d`,
  tổng hệ số 43.025.566.573.
- Gate tại `f95e367`: audit độc lập không có blocker; 144 test nguồn và 123 test
  tích hợp trên composed head đều xanh, Ruff/format/diff-check sạch. Replay
  Family 4/9/10 giữ nguyên semantic outputs; production không có routing theo
  bank/file/page/note.

## Family 12 closure

Artifact OFFICIAL:
`/tmp/gemini-family12-official-c58983d.json`, SHA-256
`a88ed2a3d003107171b465d56bd532d76f98eb0dda35c91a6b5643f158f22d93`,
2.989.104 byte, sweep
`gjfafsv1:sweep:e19dfeb014361879a2c913e04384b86ebd98c814092fc3f2b465ad54ed47c83a`.

- Kết quả: `READY=84`, `NOT_OBSERVED=56`, `UNRESOLVED=0`, 903 mappings,
  1.806 MONEY cells, 419 closure equations và không tạo repair job.
- Query chỉ đọc 8.947 page-version đã chọn. Từ 1.463 indexed row hits trong
  267 tables, resolver tạo đúng 84 accepted regions; mọi table gần đều có
  disposition có kiểu và toàn bộ query evidence được replay lại từ SQLite.
- Shared structural-context resolver dùng section/table title, narrative và
  owner cục bộ hoặc preceding carry tối đa hai trang, với population reset và
  hard-negative fence. Không có routing theo bank, file, page hay source hash.
- Collapsed direct frontier bảo đảm subtotal đã chứng minh thay thế descendants
  thay vì cộng đồng thời cả cha và con. Leading/trailing population carrier,
  peer equation, later total và detached-root đều phải khép trên mọi lane.
- Đối chiếu E-0118 giữ nguyên chính xác 57 leaf mappings (fingerprint
  `662fee71ad552826783fe06f3e4effaf36ffb76862ae279a3bb76ef3c4c5cabd`)
  và sáu root mappings (fingerprint
  `d42d462a8ea7b5dca345cc82f5dbc1c268530d16877011c580604f6cb6768a2a`).
- Gate code tại `b5fdcee`, composed tại `c58983d`: audit độc lập không có
  blocker; 178/178 test, Ruff, format, diff-check và fsck sạch. Artifacts
  Family 4/9/10/11 revalidate với SHA không đổi, và legacy Family 12 giữ
  nguyên byte.

## Families 13–25 closure

- Family 13 `PROVISION_MOVEMENT_ROLLFORWARD`: `READY=140`, `UNRESOLVED=0`,
  1.281 mappings. Full selected-frontier/query/candidate SQLite replay, exact
  period/unit/continuity/equation receipts and the bounded table-repair
  projection are sealed; Gemini repair uses only the minimal observation
  contract and all graph/equation decisions remain local code.
- Family 14 `PURCHASED_DEBT_ACTIVITY`: `READY=64`, `NOT_OBSERVED=76`,
  `UNRESOLVED=0`, 254 mappings. Exact sibling-component, period, unit and total
  closures replay from the frozen page store; the 76 absence cases emit no
  candidate or mapping.
- Family 15 `CUSTOMER_DEPOSIT_CLASSIFICATION`: `READY=140`, `UNRESOLVED=0`,
  2.206 mappings. One declarative owner/type/currency/customer resolver handles
  row/column, stacked, nested and continuation layouts without bank/file/page
  routing.
- Family 16 `INVESTMENT_SECURITIES`: `READY=140`, `UNRESOLVED=0`, 2.149
  mappings and 995 exact closure receipts. The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family16-investment-securities/sweep.json`,
  SHA-256
  `4032d2308683865dec34d17f92558e380dbca0fa7b2ded00460227693c2b2be1`.
  It replays all 8.947 selected page versions and matches all 112 comparable
  historical values. Code commit `bc8f164`; cumulative results DB has 16
  current selections, passes `quick_check` and has no foreign-key failures.
- Family 17 `OTHER_LONG_TERM_INVESTMENTS`: `READY=140`, `UNRESOLVED=0`,
  429 mappings and 458 exact closure receipts. One owner/reset-fenced resolver
  handles optional direct children, repeated-period summary/detail tables,
  same-page/adjacent continuation, carrying/reporting-currency metric columns,
  provision signs, anonymous gross/net totals and equation-proven blank zeros
  without bank/file/page routing. The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family17-other-long-term-investments/sweep.json`,
  SHA-256
  `6ca7d36b4187f3b049f22d42671f464ab7338b7521c8096793a5e4bd839c32f9`;
  audit SHA-256
  `023c59caa66fa56d7dc3881ee02883f3f7419951a4d2cd73a04785cf9a177154`.
  Full SQLite replay covers all 8.947 selected page versions and 292 accepted
  fragments; both E-0068 and E-0122 match exactly (57/57 mappings). Code commit
  `b10b054`; detached audit passed 171 tests, lint/format and exact artifact
  reproduction. The cumulative results DB now has 17 current selections,
  passes `quick_check` and has no foreign-key failures.
- Family 18 `TANGIBLE_FIXED_ASSETS_ROLLFORWARD`: `READY=72`,
  `NOT_OBSERVED=68`, `UNRESOLVED=0`, 875 mappings and 1.247 exact equations.
  One declarative fixed-asset roll-forward engine handles cost, accumulated
  depreciation and carrying-value branches, visible subtotals, duplicate
  movement rows, equation-proven right-edge shifts, source order, period and
  unit without bank/file/page routing. Period dates come from exact local
  endpoints or typed primary-statement/balance-sheet evidence; a bare year is
  never expanded to 31 December. The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family18-tangible-fixed-assets/sweep.json`,
  SHA-256
  `7d34b2cf41dbe05dc119b02f6d25b1d8940ea42aae827a9793b5d164b6ff8475`;
  audit SHA-256
  `b2b988992b50a53c5fe62051c813b4e17184f010ce61757d35f70da54fa2392a`.
  Full SQLite replay covers all 8.947 selected page versions; E-0069/E-0123
  match 16/16 historical dispositions and 140/140 values. Code commit
  `c0c1978`; 217 focused/adjacent tests passed. The cumulative results DB now
  has 18 current selections, passes `quick_check` and has no foreign-key
  failures.
- Family 19 `LEASED_FIXED_ASSETS_ROLLFORWARD`: `READY=0`,
  `NOT_OBSERVED=140`, `UNRESOLVED=0`, 0 mappings. Đây là absence closure có
  thẩm quyền, không phải family bị bỏ qua: indexed query đã replay toàn bộ
  8.947 selected page versions, mọi document đều có typed disposition và
  không có accepted cluster. E-0070/E-0124 khớp chính xác 16/16 bounded
  absence records. Cùng fixed-asset engine của Family 18 được cấu hình thành
  hai signed branch và optional carrying control; không thêm bank/file/page
  route hay prompt Gemini riêng. The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family19-leased-fixed-assets/sweep.json`,
  SHA-256
  `8bef6a9d7656cb5a6190620e670e9f2637dfb4beab709ff3db15412d1e10900d`;
  audit SHA-256
  `e657c27e230403e92c4d891dc2767df7643de9a07531f62e03dff25d68121b21`.
  Implementation commit `b568bd9`, generic claim-boundary follow-up
  `d7412c0`; 31 focused tests and 178 adjacent family tests passed. The
  cumulative results DB now has 19 current selections, passes `quick_check`
  and has no foreign-key failures.
- Family 20 `INTANGIBLE_FIXED_ASSETS_ROLLFORWARD`: `READY=72`,
  `NOT_OBSERVED=68`, `UNRESOLVED=0`, 829 mappings and 1.120 exact closure
  equations. The same declarative fixed-asset engine now handles cost,
  accumulated amortization, carrying value, exact one-or-more-child visible
  subtotal blocks, configured direct-role fallback and the separate
  fully-amortized-still-in-use disclosure. That disclosure is projected by
  deterministic code from 33 typed table values and 23 dated narratives; no
  provider prompt contains graph, equation or ReportNormId logic. Exact SQLite
  replay covers all 8.947 selected page versions and rebuilds every accepted
  candidate from canonical source JSON. E-0071/E-0125 match 16/16 historical
  document dispositions and 139/139 values. The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family20-intangible-fixed-assets/sweep.json`,
  SHA-256
  `976674f8c46fa88a4e26fdbf764b5338535d7351ebdf97c29134b59e89015de0`;
  audit SHA-256
  `e416d39308149f62b59ea8938b80a2b6d5a5211b96060c7580fb04b3d9417867`.
  Implementation commit `0226a90`; 155 focused/adjacent tests passed and
  Family 18/19 corpus regressions retained their exact semantic axes. The
  cumulative results DB now has 20 current selections, passes `quick_check`
  and has no foreign-key failures.
- Family 21 `INVESTMENT_PROPERTY_ROLLFORWARD`: `READY=12`,
  `NOT_OBSERVED=128`, `UNRESOLVED=0`, 105 mappings and 185 exact closure
  equations. The shared declarative fixed-asset engine now covers complete
  investment-property roll-forwards, cost-only fragments, contiguous sibling
  populations, note-level carrying summaries and typed balance-sheet carrying
  controls. All aggregation, period/unit resolution, graph closure and schema
  mapping remain deterministic local code; no prompt contains family equations
  or ReportNormIds. Exact SQLite replay covers all 8.947 selected page versions
  and rebuilds every accepted source receipt. E-0072/E-0126 match 16/16
  historical document dispositions and 26/27 values; the one transparent
  refinement maps source label `Khấu hao trong năm` to the specific
  depreciation-charge leaf instead of the older increase subtotal. The
  OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family21-investment-property/sweep.json`,
  SHA-256
  `bbf1540a7a3b4bb4732a618c25b3166e6010c5c00dbe07c07c27e08a25554766`;
  audit SHA-256
  `6d5e629c07c22caf501d84bcbe3ba27206e5de505dfbb48757a33bdd33cac82e`.
  Implementation commit `7a18647`; detached audit passed 122 focused/adjacent
  tests, lint/format/compile/diff/fsck, and reproduced both artifact hashes
  byte-for-byte. The cumulative results DB now has 21 current selections,
  passes `quick_check` and has no foreign-key failures.
- Family 22 `OTHER_ASSETS`: `READY=78`, `NOT_OBSERVED=62`,
  `UNRESOLVED=0`, 1.290 mappings and 374 exact closure equations. One generic
  multi-table hierarchical engine inventories every declared-role table inside
  the authenticated owner/reset fence, handles same-table, sibling-table,
  multi-page, repeated-period and bare-year source layouts, and keeps source
  rows with no exact schema leaf typed but unmapped. Blank source cells are
  promoted to zero only through an exact visible equation; label-only
  `GROUP`/`SUBTOTAL`/`TOTAL` rows are structural carriers and never become
  invented zero mappings. All period/unit resolution, duplicate-role
  aggregation, graph closure and schema mapping remain deterministic local
  code; no Gemini prompt, bank/file/page route or source-value rule was added.
  Exact SQLite replay covers all 8.947 selected page versions and rebuilds 297
  fragments in 78 accepted clusters. E-0073/E-0127 match 16/16 historical
  document dispositions and 192/192 mappings; the combined comparator is
  208/208 exact. The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family22-other-assets/sweep.json`,
  SHA-256
  `f03b49fedb5d9cba1efe73c17e4cdee9afb80df637fd05d476894814ae2189c8`;
  audit SHA-256
  `3805feb2728267068e5668bc4d0b54074637508f72bf407e515acdb40f7036f1`.
  Implementation commit `db43481`; 145 focused/adjacent tests, Ruff, format,
  compile and JSON/diff checks passed. A separate public SQLite audit replay
  reproduced all four semantic axes, and the cumulative results DB now has 22
  current selections, passes `quick_check` and has no foreign-key failures.
- Family 23 `GOVERNMENT_SBV_LIABILITIES`: `READY=140`,
  `NOT_OBSERVED=0`, `UNRESOLVED=0`, 739 mappings and 411 exact closure
  equations. The existing generic multi-table hierarchical engine was extended
  only through declarative, opt-in owner surfaces, hierarchy-path role scope,
  canonical top-level frontier and structural-label projection. It covers
  aggregate-only, central-bank facility, Treasury currency/tenor, repo and
  other-liability layouts without bank/file/page routing. A family root may be
  derived only from a complete canonical top-level frontier; nested components
  are excluded from that sum, preventing double counting. All graph, period,
  unit, equation and schema decisions remain deterministic local code and no
  Gemini prompt contains ReportNormIds or accounting equations. Exact SQLite
  replay covers all 8.947 selected page versions and rebuilds 140 fragments in
  140 accepted clusters. E-0074/E-0128 match 16/16 historical dispositions and
  70/75 historical mappings. The five transparent refinements preserve source
  evidence while correcting legacy conflation: VCB's VND payment and term
  deposits are no longer merged; BID's Finance-Ministry deposit uses dedicated
  RNID 6072; one ACB repo keeps its source-semantic role; and CTG's previously
  combined borrowing/repo value is represented by its two visible source rows.
  The OFFICIAL sweep is
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family23-government-sbv-liabilities/sweep.json`,
  SHA-256
  `371508e82913ae03b8ec002e6c006daf1667d1a1a0cbf3089a3bcedb029007f3`;
  audit SHA-256
  `a92637d40a4703ee8d092f06856bea4286b2e1a0ec73d9bb243157fd63d9b9d9`.
  Implementation commit `522f0b2`; 95 focused/adjacent tests, Ruff, format,
  compile, JSON and diff checks passed. Family 22's public SQLite replay stayed
  exact. The cumulative results DB now has 23 current selections, passes
  `quick_check`, has no foreign-key failures or SQLite sidecars, and is sealed
  at SHA-256
  `44c7c33669a940ca1f59fad961390cadfa963798eb883ca3ec918130fdf39d8d`.
- Family 24 `ENTRUSTED_INVESTMENT_RISK_CAPITAL`: `READY=76`,
  `NOT_OBSERVED=64`, `UNRESOLVED=0`, 174 mappings và 117 exact closure
  equations. Cùng generic multi-table hierarchical engine xử lý owner/reset
  fence, organization/person aggregate, currency branches, self-contained
  structural-parent labels, multi-line ODA/NHNN programmes và label-only
  structural group có một hoặc nhiều direct children. Group chỉ được project
  sau khi source total đóng chính xác trên mọi lane; các currency fragment
  chung trong family khác không thể tự claim scope. Tất cả graph, period, unit,
  equation và schema decisions vẫn ở deterministic local code; không thêm
  prompt Gemini, bank/file/page route hoặc source-value rule. Exact SQLite
  replay phủ đủ 8.947 selected page versions và dựng lại 76 accepted clusters.
  E-0075/E-0130 khớp chính xác 16/16 historical dispositions và 26/26 mappings;
  combined comparator là 42/42 exact. OFFICIAL sweep là
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family24-entrusted-investment-risk-capital/sweep.json`,
  SHA-256
  `49e2fdf65c9d6b9f3a99cef34d825d2f1ba3a2b9b787d6ed6a5edb271aefade8`;
  audit SHA-256
  `d8cd460e774f16e2a35faf72dc6c6e1e1e850a6cf26aeaa51f9a19187eee519f`.
  Implementation commit `728c8e4`; 45 focused và 98 focused/adjacent tests,
  Ruff, format, compile, JSON và diff checks đều xanh. Cumulative results DB
  có 24 current selections, `quick_check` và foreign keys sạch, không có
  SQLite sidecar, SHA-256
  `89b2b316d73726208101dc860bc776803e1dca472260b6eb74a5b2397af73e1c`.
- Family 25 `ISSUED_VALUABLE_PAPERS`: `READY=140`, `NOT_OBSERVED=0`,
  `UNRESOLVED=0`, 1.228 mappings và 849 exact closure equations. Cùng generic
  multi-table hierarchical engine xử lý cả layout khoản mục ở hàng/kỳ ở cột
  và layout instrument ở cột/tenor ở hàng; instrument parent, tenor child,
  printed subtotal/root, repeated-period tables, source-visible hoặc derived
  `Kỳ phiếu + Trái phiếu`, unique equation-sealed right shift và duplicate
  source populations đều dùng primitive khai báo chung. Dash/blank không được
  tự dịch để tạo alignment; chỉ suffix chứa giá trị khác zero mới là repair
  candidate và toàn bộ horizontal/vertical equations phải đóng duy nhất. Mọi
  graph, period, unit, alignment, equation và schema mapping vẫn ở local code;
  không thêm prompt Gemini hoặc route theo bank/file/page/value. Exact SQLite
  replay phủ đủ 8.947 selected page versions, dựng lại 186 fragments trong 140
  accepted clusters và khớp 16/16 historical dispositions. E-0076/E-0131
  khớp 134/136 historical mapping values. Hai refinement có source authority
  đều ở ACB 2026-Q2: oracle cũ bỏ visible tenor 5-year khỏi `CD_MEDIUM` và
  `BOND_MEDIUM`, trong khi current source frontier giữ hàng đó nên hai
  instrument totals và family root đóng chính xác. OFFICIAL sweep là
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family25-issued-valuable-papers/sweep.json`,
  SHA-256
  `a46d21ffdec18f6079447e1b4298be85beb57a385fc11ba997fb9aa0286c5b54`;
  audit SHA-256
  `02832e5c621ab42786961932b988f53d11fc6460926525de4221ff01dfb9b09a`.
  Implementation commit `45fed8b`; 87 focused/adjacent tests, Ruff, format,
  compile, JSON, diff và fsck checks đều xanh. Cumulative results DB có 25
  current selections, `quick_check` và foreign keys sạch, không có SQLite
  sidecar, SHA-256
  `ec043ab2956900adabdec60805e4ebf6e9a43be505304b7ca56e59fc8b086d28`.
- Family 26 `OTHER_PAYABLES_LIABILITIES`: `READY=140`, `NOT_OBSERVED=0`,
  `UNRESOLVED=0`, 809 mappings và 334 exact closure equations. Cùng generic
  multi-table hierarchical engine xử lý family root, internal/external
  structural groups, employee/tax/other-payable/risk-provision/welfare leaves,
  source-only residual rows và nhiều detail table trong một owner/reset fence.
  Source-visible root chỉ được nhận khi đúng một table-local direct-frontier
  equation đóng; residual không alias chỉ được project khi đã được exact source
  equation tiêu thụ và table có residual anchor. Structural context total bị
  loại trước khi cộng các residual leaf có nhãn và source table disjoint, nên
  parent/detail không bị double-count. Hierarchy path do Gemini gộp
  `parent\n- child` được canonicalize theo exact visible line, không ép model
  trả lại một serialization riêng. Tất cả graph, period, unit, equation,
  residual projection và ReportNormId mapping vẫn là deterministic local code;
  không thay prompt hoặc route theo bank/file/page/value. Exact SQLite replay
  phủ đủ 8.947 selected page versions và dựng lại 220 fragments trong 140
  accepted clusters. E-0077/E-0132 khớp 16/16 historical dispositions và 92/92
  mappings; combined comparator là 108/108 exact. OFFICIAL sweep là
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family26-other-payables-liabilities/sweep.json`,
  SHA-256
  `9c991f01b45c27224b71cdca9802dd92b41d5fa8cfb730ad2e74f91db62e0f81`;
  audit SHA-256
  `2295c1ce570e83c7ccf36dd416cc3b3a405e6f5d2a611a85df8eb8576a05fc3a`.
  Implementation commit `68f602b`; detached audit tái tạo hai artifact
  byte-for-byte, 139 focused/adjacent tests, Ruff, format, compile, JSON và diff
  checks đều xanh. Cumulative results DB có 26 current selections,
  `quick_check` và foreign keys sạch, không có SQLite sidecar, SHA-256
  `4cdb15ae7260d45476c24a50f57aa3e6b2c1437e016e75a1498e0cb801035957`.
- Family 27 `CAPITAL_AND_FUNDS`: `READY=137`, `NOT_OBSERVED=0`,
  `UNRESOLVED=3`, 1.295 mappings và 2.252 horizontal/vertical closure
  equations. Generic equity-matrix engine nhận cả component-columns lẫn
  component-rows, khóa opening/closing theo source date thay vì thứ tự trang,
  giữ optional source-only component trong tổng nhưng không map sang schema
  leaf, và chỉ map movement total khi source hiển thị đúng một role rõ ràng.
  Monotone row-alignment solver chỉ tái gán những digit token đã nhìn thấy khi
  nghiệm horizontal+vertical graph là duy nhất; 9 receipts sửa được năm tài
  liệu mà không tạo hoặc đổi digit. Ba tài liệu BID/VIB ordinal 25/33/114 giữ
  `UNRESOLVED` và `mappings=[]` vì JSON nguồn thật sự thiếu hoặc đặt sai token
  khiến không tồn tại horizontal exact placement. Ảnh PDF đã xác nhận bảng
  nguồn đọc được; follow-up chỉ được dùng observation prompt cố định
  `cell_id + source_text` cho đúng các ô thiếu, không được backsolve chữ số,
  route theo bank/page hay làm prompt family-specific. Exact SQLite replay phủ
  đủ 8.947 selected page versions, 143 fragments trong 140 accepted clusters;
  137 READY clusters có 95 period-block receipts. E-0078/E-0133 khớp 128/128
  historical values ở 15 READY documents; 11 historical values còn lại cùng
  thuộc BID ordinal 25 và được ghi typed `CURRENT_UNRESOLVED`, không phát sinh
  mapping giả. OFFICIAL sweep là
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-family-results/family27-capital-and-funds/sweep.json`,
  SHA-256
  `55b21614c1123ea4fb4105f69f1ea1fcdfa17d32cee3eae1ba6af20955adfa47`;
  audit SHA-256
  `d299814d5a502f93870e2308ed1d4791f97ff37cdc3a1370e92053e0bca93dfb`.
  Implementation commit `99eb423`; 229 focused/adjacent tests và 35 page/store
  tests, Ruff, format, compile, JSON và diff checks đều xanh. Cumulative
  results DB có 27 current selections, `quick_check` và foreign keys sạch,
  không có SQLite sidecar, SHA-256
  `b6f6e49aca7539ed683f353561569f56bced9f4ad3748d341cb0e051b75dcf4e`.

## Next gate

Family 28 là `INTEREST_INCOME` bắt đầu tại ReportNormId 1143. Đo khả năng tái sử
dụng của generic owner/reset-fenced two-period hierarchy engine trên full-corpus
indexed census 8.947 trang, rồi khóa comparator E-0079 và E-0134. Thuật toán
phải bao quát interest income total cùng các khoản tiền gửi, cho vay, đầu tư
chứng khoán nợ, bảo lãnh, mua bán nợ và hoạt động tín dụng khác; parent total có
thể đứng trước, đứng sau hoặc ở table sibling nhưng không được cộng trùng với
children. Period, unit, dấu âm/dash, table continuation, source-only residual và
equation phải do deterministic local code xử lý. Gemini tiếp tục dùng page JSON
prompt tối giản; chỉ typed missing-row/column/context mới được tự động chuyển
sang một prompt version bounded đã khai báo, không route theo bank/file/page.
Chỉ promote OFFICIAL sau exhaustive inventory, query/candidate SQLite replay,
equation receipts, historical comparator và toàn bộ disposition 140 tài liệu
được niêm phong rõ ràng.
