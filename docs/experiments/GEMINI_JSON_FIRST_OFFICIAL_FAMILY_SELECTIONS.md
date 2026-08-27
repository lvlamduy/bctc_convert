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

Tại checkpoint này database có đủ đúng chín current selection liên tục từ
Family 1 đến Family 9. Family 10 chưa được promote và không được bỏ qua.

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

## Next gate

Family 10 là `LOAN_CURRENCY_CLASSIFICATION`. Phải preflight từ indexed Gemini
JSON và chỉ promote sau khi Family 9 current selection đã replay đúng như trên.
