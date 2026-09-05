# Điểm bàn giao an toàn khi chuyển máy — 2026-09-05

Tài liệu này là điểm khởi động lại có thẩm quyền cho chuỗi đánh giá
Gemini-JSON-first trên corpus BCTC ngân hàng 2025–2026. Mục tiêu là cho phép
một phiên Codex mới tiếp tục đúng byte code, đúng corpus, đúng các quyết định
thuật toán và đúng hàng đợi đang dở sau khi máy hiện tại bị xóa hoàn toàn.

Không dùng các thống kê cũ trong `CURRENT_STATUS.md` để ghi đè checkpoint này
nếu chúng được ghi trước ngày 2026-09-05. Khi có khác biệt, ưu tiên theo thứ tự:

1. commit Git cuối cùng và run record S3 đã restore-verify;
2. tài liệu checkpoint này;
3. ledger full271 riêng của từng family;
4. diagnostic tạm trong `/dev/shm` chỉ để tiếp tục điều tra, không phải release.

## 1. Tóm tắt khẩn cấp

- Đã xử lý tới **Family 40**.
- Hàng đợi chưa terminal còn đúng ba family:
  **F36 `OPERATING_EXPENSE`**, **F37 `CREDIT_RISK_PROVISION_EXPENSE`** và
  **F39 `INCOME_TAX`**.
- Không mở family mới trước khi khép cả ba family trên.
- Tại lúc đóng phiên, mọi pytest/replay/runner/provider job dài đã dừng; không
  còn request Gemini, Agy hoặc OpenRouter đang bay.
- Không cần và không được gọi lại provider để hoàn thiện ba family. Corpus JSON,
  PDF-visible evidence, source-repair receipt và các diagnostic hiện có đủ để
  làm phần còn lại offline.
- Worktree có thẩm quyền là `/tmp/bctc-ai-27-bank`, không phải checkout cũ ở
  `/workspace/bctc-ai`.
- Branch có thẩm quyền: `codex/27-bank-2025-current`.
- Remote Git: `https://github.com/lvlamduy/bctc_convert.git`.
- HEAD trước commit migration: `d6260a3cfe25370ae32e885d288cacc100460531`.
- Commit code/test/evidence migration đã push:
  **`7b2e33d900d6d10fe6e339cd31847b8a86707060`**.
- Commit tài liệu receipt cuối cùng là tip của branch và được bind trong
  `migration-manifest-final.json` trên S3; dùng `git ls-remote` để kiểm tip thay
  vì cố nhúng hash tự tham chiếu vào chính commit chứa tài liệu này.
- Prefix S3 migration cuối cùng:
  **`s3://test-s3-duylv/bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/`**.

Một backup chỉ được xem là đạt khi đã tải ngược và kiểm SHA-256, không chỉ vì
lệnh PUT thành công. Receipt cuối cùng có key cố định
`bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/manifest/migration-manifest-final.json`.

## 2. Phạm vi dữ liệu và corpus bất biến

Phạm vi production hiện hành là 27 ngân hàng, báo cáo từ năm 2025 đến hiện tại.
Trong đó 19 ngân hàng mới là `ABB, BAB, BVB, EIB, KLB, LPB, MSB, NAB, NVB,
OCB, PGB, SGB, SHB, SSB, STB, TCB, TPB, VAB, VBB`; tám ngân hàng cũ
`ACB, BID, CTG, HDB, MBB, VCB, VIB, VPB` chỉ tái sử dụng extraction đã có.
Không gửi lại provider cho tám ngân hàng cũ.

Corpus full271 đã hoàn tất chuyển PDF thành Gemini JSON cho **271/271 PDF** và
**14.945/14.945 trang**. Các đường dẫn runtime hiện tại:

Kiến trúc có thẩm quyền là **PDF → Gemini JSON → kiểm chứng/receipt →
SQLite/database**. Không dùng PPOCR6, VietOCR, geometry OCR, DeepSeek OCR,
Gemma hoặc PaddleOCR trong đường production hiện tại. Các code/model/cache/data
chỉ phục vụ các chiến lược cũ đó không thuộc checkpoint phục hồi; object S3
liên quan phải được xóa theo inventory có kiểm tra, không tải lại sang máy mới.

- Root full271:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts`.
- Immutable full271 manifest index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`.
- Full271 validation report:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-validation-reports/ded4ee5ccfd69733e89e96d18ec3ecec20d5a6c114eba2b96ac5d5ff756ceb06.json`.
- Full271 SQLite store:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`.
- Root common204:
  `/dev/shm/bctc-ai-27-bank-family-live-v1`.
- Immutable common204 manifest index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`.
- Common204 SQLite store:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-freeze-inputs/store-a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220.sqlite3`.
- Corpus lịch sử old140:
  `/tmp/gemini-json-first-corpus-production-v2`.
- Paid extraction/run evidence đã đóng:
  `/dev/shm/bctc-ai-27-bank-vertex-flex-run`.

Các thư mục `f*` và `family*` dưới `/dev/shm` là diagnostic, render, SQLite,
trial, receipt và visual evidence cần giữ nguyên byte. Archive migration giữ
toàn bộ material Gemini/database này nhưng loại theo path mọi PPOCR/VietOCR,
geometry, DeepSeek, Gemma và PaddleOCR. Một số JSON/receipt trong đó là thử
nghiệm lỗi có chủ đích; chỉ ledger và final run record mới được dùng làm release
authority.

## 3. Trạng thái terminal tới Family 40

Chuỗi hiện hành đã đi qua Family 40. Các family có **release ledger full271
được ghi trực tiếp trong Git** tại checkpoint này là:

| Family | Mã family | Ledger có thẩm quyền |
| ---: | --- | --- |
| 16 | `INVESTMENT_SECURITIES` | `docs/experiments/staging/family-16-investment-securities-full271-visual-audit-v1.md` |
| 17 | `OTHER_LONG_TERM_INVESTMENTS` | `docs/experiments/staging/family-17-other-long-term-investments-full271-visual-audit-v1.md` |
| 18 | `TANGIBLE_FIXED_ASSETS` | `docs/experiments/staging/family-18-tangible-fixed-assets-full271-visual-audit-v1.md` |
| 20 | `INTANGIBLE_FIXED_ASSETS` | `docs/experiments/staging/family-20-intangible-fixed-assets-full271-visual-audit-v1.md` |
| 22 | `OTHER_ASSETS` | `docs/experiments/staging/family-22-other-assets-full271-visual-audit-v1.md` |
| 24 | `ENTRUSTED_INVESTMENT_RISK_CAPITAL` | `docs/experiments/staging/family-24-entrusted-investment-risk-capital-full271-visual-audit-v1.md` |
| 25 | `ISSUED_VALUABLE_PAPERS` | `docs/experiments/staging/family-25-issued-valuable-papers-full271-visual-audit-v1.md` |
| 26 | `LOAN_INTEREST_ACCRUAL_CLASSIFICATION` | `docs/experiments/staging/family-26-loan-interest-accrual-classification-full271-visual-audit-v1.md` |
| 27 | `CAPITAL_AND_FUNDS` | `docs/experiments/staging/family-27-capital-and-funds-full271-visual-audit-v1.md` |
| 28 | `INTEREST_INCOME` | `docs/experiments/staging/family-28-interest-income-full271-visual-audit-v1.md` |
| 29 | `INTEREST_EXPENSE` | `docs/experiments/staging/family-29-interest-expense-full271-visual-audit-v1.md` |
| 30 | `SERVICE_ACTIVITY` | `docs/experiments/staging/family-30-service-activity-full271-visual-audit-v1.md` |
| 31 | `FX_GOLD_ACTIVITY` | `docs/experiments/staging/family-31-fx-gold-activity-full271-visual-audit-v1.md` |
| 32 | `TRADING_SECURITIES_ACTIVITY` | `docs/experiments/staging/family-32-trading-securities-activity-full271-visual-audit-v1.md` |
| 33 | `INVESTMENT_SECURITIES_ACTIVITY` | `docs/experiments/staging/family-33-investment-securities-activity-full271-visual-audit-v1.md` |
| 34 | `COMBINED_SECURITIES_NET` | `docs/experiments/staging/family-34-combined-securities-net-full271-visual-audit-v1.md` |
| 35 | `CAPITAL_CONTRIBUTION_DIVIDEND_INCOME` | `docs/experiments/staging/family-35-capital-contribution-dividend-income-full271-visual-audit-v1.md` |
| 38 | `OTHER_ACTIVITY` | `docs/experiments/staging/family-38-other-activity-full271-visual-audit-v1.md` |
| 40 | `CASH_EQUIVALENTS` | `docs/experiments/staging/family-40-cash-equivalents-full271-visual-audit-v1.md` |

`R/N/U` dưới đây lần lượt là `READY / NOT_OBSERVED / UNRESOLVED`. Terminal
không đồng nghĩa bắt buộc `U=0`: một `U` có PDF-visible conflict thật, được
audit đầy đủ và fail-closed vẫn là disposition terminal hợp lệ.

- F33 full271: `271R / 0N / 0U`, 771 mapping.
- F35 full271: `217R / 52N / 2U`, 639 mapping; old140:
  `133R / 7N / 0U`.
- F38 full271: `270R / 0N / 1U`, 1.186 mapping; common204:
  `204R / 0N / 0U`, 885 mapping.
- F40 full271: `200R / 65N / 6U`, 995 mapping; common204:
  `150R / 50N / 4U`, 760 mapping. F40 đã qua 59 test focused và 297 test
  broad tại release checkpoint.

Không dùng bảng 140-PDF lịch sử trong `COMPLETED_TM_FAMILIES.md` để thay cho
các con số full271 trên. Tài liệu đó vẫn hữu ích cho lịch sử schema và biến thể.

## 4. Hai file dùng chung bị đóng băng

Ba family đang dở phải tiếp tục bằng adapter/config riêng. Không sửa hai file
dùng chung sau nếu chưa có quyết định kiến trúc mới và replay toàn bộ family
đã release:

| File | SHA-256 bắt buộc |
| --- | --- |
| `src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py` | `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2` |
| `scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py` | `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5` |

Kiểm lại ngay sau clone:

```bash
sha256sum \
  src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py \
  scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py
```

Nếu khác một byte, dừng trước replay; không tự cập nhật expected hash để làm
test xanh.

## 5. F36 — `OPERATING_EXPENSE` — đang dở

### Điểm đã đạt

- Focused suite gần nhất: **49/49 PASS**.
- Python compile và Ruff đã xanh ở thời điểm kiểm tra.
- Sau đó runner có một số patch nhỏ cuối; bytes runner hiện tại Ruff xanh nhưng
  runner tests chưa được chạy lại sau đúng patch cuối. Vì vậy 49/49 là bằng
  chứng gần nhất, không được coi là acceptance của bytes cuối.
- Diagnostic cũ `/dev/shm/f36-full271-current-eval-v2.json`, SHA-256
  `f988eaad65e21bdb52ce87ad69f45cad5622b55e35d88d6d1ed0ee4c13ce033b`,
  cho `252R / 7N / 12U`, 2.819 mapping. Nó có trước các sửa cuối,
  chỉ dùng để định vị lỗi cũ.
- Mục tiêu được kỳ vọng sau sửa là khoảng `269R / 0N / 2U`, nhưng **chưa được
  chứng minh bằng run authoritative**. Không ghi con số kỳ vọng thành kết quả.

### Hash code/config tại lúc dừng

| File | SHA-256 |
| --- | --- |
| `config/families/tm-operating-expense-topology-v1.json` | `6aba6294ec394eadda4e4ed6adc1ff09df92391afd17cd603687378086760df7` |
| `config/families/tm-operating-expense-evaluation-v1.json` | `61434a30c6ed803a8a7f7e2afa23505f134aaed9c961bb5949bdcc70374e9280` |
| `config/families/tm-operating-expense-schema-binding-v1.json` | `ba44624bb4ebcf8cae190e189c62d5d24acf457993c63062ce11b76ad36361cd` |
| `config/families/tm-operating-expense-source-repair-v1.json` | `c484644f7db79fad9aacd245f84ed7cfce32ef657ccf77c92c5d6e462a722997` |
| `src/bctc_ai/evaluation/gemini_json_operating_expense_family_v1.py` | `9af2d53e0e27bd88f5322144f660724eb5d7765b8fc34ca51cd58775efd2ffad` |
| `scripts/experiments/run_gemini_json_operating_expense_accounting_family_v1.py` | `4e3e369ecb5f17caad32d325b092aa817dc431a2aaa153c3b241c4a50aa4588b` |
| `tests/unit/test_gemini_json_operating_expense_family_v1.py` | `7e207cb6a1c0270658981467c333e7eee3f6df8024e02a4830cb38e9c3065d96` |
| `tests/unit/test_run_gemini_json_operating_expense_accounting_family_v1.py` | `7fc839f28f7d8d8f37327f9f98f71bd21f3431998367ebb1f44f40a1debf7010` |

Builder tạm phải được khôi phục cùng archive `/dev/shm`:

- `/dev/shm/build-f36-pdf-residual-audits-v1.py`, SHA-256
  `cea36e2698280b3ea9cf7c345c8c90609a2577b113805a4ee077b4f8ee4bc9e4`;
- `/dev/shm/build-f36-pdf-visible-source-row-audit-v1.py`, SHA-256
  `7fb35d486387880945ad19c28a820c2b4469c5622b01f866893b1be75b5880cd`;
- `/dev/shm/build-f36-source-row-coverage-from-sweep-v1.py`, SHA-256
  `928536de0fb68a3729fb8576c8d38ca5f25e80d26291773053618d8b014d13de`.

### Việc tiếp theo, đúng thứ tự

1. Cập nhật/đóng runner tests theo bytes runner hiện tại; không thay runner để
   khớp test cũ.
2. Chạy `py_compile`, focused pytest và Ruff cho toàn bộ path F36.
3. Chạy diagnostic mới trên full271 và common204, sau đó chạy coverage/no-left-
   behind. Không tái dùng `f36-full271-current-eval-v2.json` làm kết quả.
4. Đọc từng violation còn lại trên PDF-visible evidence; giữ conflict nguồn
   thật ở `UNRESOLVED`, không ép bằng phương trình.
5. Sinh và kiểm bốn config residual/PDF-visible cho full271/common204.
6. Chạy authoritative full271 và common204 với store/receipt mới; kiểm SQLite,
   observation coverage, projection, content ID và tamper gates.
7. Viết ledger
   `docs/experiments/staging/family-36-operating-expense-full271-visual-audit-v1.md`
   rồi mới đánh dấu F36 terminal.

## 6. F37 — `CREDIT_RISK_PROVISION_EXPENSE` — đang dở

### Điểm đã đạt

- Focused suite: **54/54 PASS**; Python compile, Ruff và diff check đã xanh.
- Diagnostic gần nhất được tạo trước lần reseal ID cuối:
  full271 `269R / 0N / 2U`, 1.180 mapping; common204
  `204R / 0N / 0U`, 898 mapping.
- Hai `U` còn lại là BAB document ordinal 21 và 22: nguồn nhìn thấy đồng thời
  gross/net-duration theo cách không có một binding duy nhất. Đây là ambiguity
  PDF thật; không backsolve.
- Coverage diagnostic hiện có zero violation, nhưng vì diagnostic có trước ID
  reseal nên vẫn phải chạy fresh authoritative.
- Chưa có authoritative final sweep, final DB/run record hoặc release ledger.

### Hash code/config tại lúc dừng

| File | SHA-256 |
| --- | --- |
| `config/families/tm-credit-risk-provision-expense-topology-v1.json` | `1e925d7c45ae1a967149234d1cecfb0e1910bc77fc44fc44e6bc210a7a246423` |
| `config/families/tm-credit-risk-provision-expense-evaluation-v1.json` | `be2bdb496a403da3697a4ae24c081364e8e878d4dfa9343bb30b0cc9a9d5e79d` |
| `config/families/tm-credit-risk-provision-expense-schema-binding-v1.json` | `7487b4b48edbdeb85cfb03cd822b2486353931fd5c2ea760ceb2eef010cf7884` |
| `config/families/tm-credit-risk-provision-expense-source-repair-v1.json` | `373987a246d8a85eb5a43418917c63cc20c2138714aa6ce5b31450cb06fa14a2` |
| `config/families/tm-credit-risk-provision-expense-pdf-residual-audit-full271-v1.json` | `6c6ed8194e53a8821fdc669f8406689bb1324fd347a3f7486845d16473655631` |
| `config/families/tm-credit-risk-provision-expense-pdf-residual-audit-common204-v1.json` | `6fdb4c377eea3a6e84262c4203e850950301edc721c72a08f864ca8e0ad4801` |
| `src/bctc_ai/evaluation/gemini_json_credit_risk_provision_expense_family_v1.py` | `b9f9e92c7883a4aadea639eb1ce00f7a3dfe8ccbb84372c3c62f0ac7879e0405` |
| `scripts/experiments/run_gemini_json_credit_risk_provision_expense_accounting_family_v1.py` | `6418a0064c6545f0d04b393e49d9fb3ffcbca88f2838f4250d5b88024cc70753` |
| `tests/unit/test_gemini_json_credit_risk_provision_expense_adapter_v1.py` | `8725211509ae94402b9bb79d4d04e4abe03cfa5ee03647747801e8d3d4d63bf3` |
| `tests/unit/test_gemini_json_credit_risk_provision_expense_family_v1.py` | `80367e041b8ba58e9f53fcea0697d8683ee363f8691690c23fa710be78879e8b` |
| `tests/unit/test_run_gemini_json_credit_risk_provision_expense_accounting_family_v1.py` | `3f801a43da3d1442525acc6dc89283b2a9645532d795bf5015f57399d64701ec` |

Diagnostic receipt SHAs cần giữ để so sánh, không promote:

- full indexed `e72a4f11...fc6ef`, trials `1a4a731f...f8b89a`, coverage
  `8b7002db...2fce`;
- common indexed `8bbd2895...afa18`, trials `084c7f50...fe051`, coverage
  `320a2537...b93a2`;
- PDF audit đã biết invalid: full `fa70e864...4677d`, common
  `d51331a4...82ef`.

Không dùng hai PDF-audit hash invalid làm gate release dù file vẫn được backup
để điều tra.

### Việc tiếp theo, đúng thứ tự

1. Chạy `/dev/shm/build-f37-fresh-census-v2.py` để dựng lại census full/common
   bằng config/ID hiện tại.
2. Chạy `/dev/shm/build-f37-fresh-pdf-visible-audits-v2.py` để sinh lại audit;
   không copy hai audit invalid.
3. Validate residual specs và chạy focused/shared tests.
4. Chạy authoritative `final-v4` cho full271 và common204.
5. Kiểm expansion, content IDs, SQLite integrity, observation coverage và
   projection giữa common204/full271.
6. Viết ledger
   `docs/experiments/staging/family-37-credit-risk-provision-expense-full271-visual-audit-v1.md`
   rồi mới đánh dấu terminal.

## 7. F39 — `INCOME_TAX` — đang dở và là ưu tiên đầu tiên

### Điểm đã đạt

- Focused suite trên bytes hiện tại: **73/73 PASS**; Ruff xanh.
- Patch cuối trong `_candidate_source_row_axis` đã thêm candidate tổng quát
  `closure_receipt.source_only_unmapped_rows`, sửa scan canonical triple-source.
- Diagnostic trước patch/review cuối: full271 `270R / 0N / 1U`, 1.127 mapping.
  LPB document ordinal 74 là conflict PDF thật và có thể tiếp tục giữ `U`.
- Kết quả trên **chưa phải acceptance**, vì reviewer còn sáu blocker bắt buộc
  bên dưới. Không viết ledger hay chạy final trước khi có regression cho cả sáu.

### Hash code/config tại lúc dừng

| File | SHA-256 |
| --- | --- |
| `config/families/tm-income-tax-adapter-v1.json` | `770a578e4ef752c97791e81469f8d09beb76088f9ec88ef594cde9af915babdf` |
| `config/families/tm-income-tax-source-repair-v1.json` | `9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4` |
| `config/families/tm-income-tax-topology-v1.json` | `da8fbcbf29dd5f37fc4f69b56bec5a08c106607fe1ba1fb096255e288d3bee43` |
| `config/families/tm-income-tax-evaluation-v1.json` | `f2439c1c46fa95ac189f267e06afbd7d9529d365e8a73e77ab13dfee482daec0` |
| `src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py` | `cf2653da462fe01b8e8c8708900cc050f04ff93b37b3a0244647e739ecda98d1` |
| `tests/unit/test_gemini_json_income_tax_family_v1.py` | `4860332fb533bdb5eba8984631f22a44ccac431f0dcf5b437ec4875973dc2f48` |

### Sáu blocker phải sửa

1. **Post-merge root closure.** Trường hợp supplemental có deferred `2/1`,
   primary có current/root `10/8`, còn deferred primary blank hiện có thể thành
   `READY` dù không khép. Khi toàn bộ current và deferred đã được quan sát, bắt
   buộc `current + deferred = root` cho từng lane; mismatch phải `U`.
2. **Supplemental exact root không được bỏ.** Supplemental root `99/99` đang có
   thể bị bỏ im lặng khi primary root là `12/9`. Phải nhận diện/bind root bổ
   sung; mismatch thành `U`, root bằng nhau chỉ là control, duplicate hoặc raw
   blank/mâu thuẫn phải fail-closed.
3. **Direct-note query vẫn phải bind repair metadata.** Đường direct-note hiện
   có thể thiếu adapter repair query, khiến source-repair spec/hash/receipt ID
   drift vẫn được chấp nhận. Mọi query, kể cả direct-note-only, phải bind đúng
   repair spec hash và receipt IDs.
4. **Hard negative/reset không được phụ thuộc `row_kind`.** Một row có label
   hard-negative nhưng `row_kind=ITEM`, hoặc hierarchy-only ancestor, đang có
   đường bypass. Fence bằng normalized label và hierarchy độc lập với
   `row_kind`.
5. **Chọn lane/đơn vị phải bất biến theo thứ tự trang.** Khi supplemental có
   lane `Million` và `VND` bằng nhau, kết quả đang phụ thuộc page order. Một lane
   VND/high-precision duy nhất phải thắng; đảo thứ tự input không đổi kết quả;
   nhiều lane VND duplicate/mâu thuẫn phải `U`.
6. **Rate frontier không được chiếm subtotal khác nghĩa.** Không coerce subtotal
   rõ ràng `TAXABLE_INCOME` thành current-tax parent. Chỉ nhận exact current-tax
   parent, hoặc subtotal generic/null nằm trong current-tax hierarchy; veto các
   known semantic role khác.

Mỗi blocker cần ít nhất một test dương và một test đối nghịch/tamper; blocker 5
phải có reverse-order invariance. Sau đó chạy focused suite, shared source-
observation tests, diagnostic full/common, residual/PDF visual audit, final
authoritative stores, projection và ledger
`docs/experiments/staging/family-39-income-tax-full271-visual-audit-v1.md`.

## 8. Thuật toán và các invariant không được phá

### 8.1 Nguồn và khả năng truy vết

- Đường dữ liệu duy nhất cần tiếp tục là PDF chính thức → Gemini JSON đã chọn →
  evaluator/receipt → SQLite/database. Không thêm lại OCR/model/geometry stack
  cũ như một fallback ẩn.
- PDF chính thức và selected Gemini JSON đã bind là nguồn dữ liệu; schema chỉ
  định nghĩa nghĩa đích, không tạo số.
- Mọi document phải bind `source_logical_name`, PDF SHA-256, byte size, số
  trang, selected page JSON/version ID và khi dùng pixel evidence phải bind
  render SHA-256/crop locator.
- Source repair là clone-only, có spec/receipt/content ID. Không sửa đè raw
  extraction và không chấp nhận repair vì nó làm phương trình đẹp hơn.
- Dòng/cột nguồn quan sát được nhưng schema không có role tương đương phải nằm
  trong `source_only_unmapped_rows`/source-only axis với provenance, không bị
  bỏ im lặng.

### 8.2 Tìm vùng và topology

- Candidate được tạo từ owner, normalized Vietnamese labels, hierarchy,
  row/column axes, page span và semantic children; không route bằng bank code,
  tên file hay số trang cụ thể.
- Bảng có thể nhiều trang, lặp header, đảo thứ tự row, gộp/tách primary và
  supplemental notes. Merge chỉ hợp lệ khi population, kỳ, scope và đơn vị
  tương thích và có duy nhất một diễn giải.
- Hard negative, reset boundary và known semantic roles là veto ở mọi
  `row_kind`; không cho metadata thiếu đi qua đường mặc định.
- Kết quả phải bất biến khi đổi thứ tự candidate/page nếu evidence tương đương.
  Nhiều candidate cùng hợp lệ nhưng dẫn đến mapping khác nhau phải `U`.

### 8.3 Kỳ, đơn vị, dấu và ô trống

- Period và unit là evidence cục bộ của đúng table/lane. Không mượn header gần
  nhất theo khoảng cách và không dùng magnitude để đoán `VND`, nghìn hay triệu.
- Giữ raw transcription. Ngoặc âm, dấu phân cách và scale chỉ normalize sau khi
  evidence đủ.
- Dấu gạch nhìn thấy và đã bind pixel/source có thể normalize thành số 0 quan
  sát được. Ô trắng là `BLANK`, **không bao giờ tự đổi thành 0**.
- Không dùng số kỳ bên cạnh hoặc tổng kế toán để bù chữ số OCR bị thiếu nếu
  không có source/pixel challenger độc lập.

### 8.4 Mapping và phương trình kế toán

- Chỉ emit RNID/role thuộc schema binding của đúng family và đúng semantic
  context. Nhãn giống nhau ở subtree khác không cho phép map chéo.
- Parent và descendants không được cộng hai lần. Mỗi equation dùng một
  exhaustive frontier rõ ràng; một source occurrence không được dùng hai lần
  trong cùng population.
- Accounting closure chỉ **corroborate hoặc veto**. Không backsolve, tự sinh
  child, sửa raw value hoặc chọn candidate chỉ vì tổng khép.
- Chấp nhận rounding chỉ khi policy được khai báo, quy mô/đơn vị phù hợp và
  receipt lưu residual. Conflict nguồn thật giữ `UNRESOLVED`.
- Multi-period/multi-lane phải khép độc lập từng lane. Không cho một lane đúng
  che lane khác sai hoặc blank.

### 8.5 Ba trạng thái disposition

- `READY`: có vùng nguồn duy nhất, period/unit/role rõ, mọi value có provenance,
  equations và no-left-behind gates cần thiết đều đạt.
- `NOT_OBSERVED`: chỉ sau bounded whole-document scan và PDF residual audit xác
  nhận không có semantic anchor phù hợp. Không dùng để che exception/runner
  error/missing artifact.
- `UNRESOLVED`: có evidence nhưng ambiguity, duplicate, source conflict,
  incompatible units/periods hoặc closure mismatch chưa thể phân xử. Fail-
  closed là kết quả đúng.

### 8.6 IDs, reproducibility và tamper resistance

- Config SHA, source-repair spec, selected JSON IDs, sweep ID, mapping/content
  ID, store receipt và run record phải tạo thành chuỗi hash khép kín.
- Thay một byte source/config/receipt phải làm verification fail. Không reseal
  expected ID bằng tay để che drift.
- Diagnostic và authoritative run phải dùng thư mục/store mới; không nối vào DB
  cũ rồi coi là reproducible.
- Full271 và common204 phải được chạy độc lập, sau đó kiểm projection của đúng
  204 document chung. Không suy common204 bằng cách chỉ sửa denominator.

## 9. Quy trình đóng một family

Thứ tự chuẩn, áp dụng cho F39 trước, rồi F36 và F37:

1. Kiểm Git commit, hai shared pins và các owned-file hashes của family.
2. Tạo môi trường Python 3.11 hoặc 3.12 sạch; cài project cùng dev extras.
3. Chạy `py_compile`, focused pytest và Ruff.
4. Chạy shared regression tối thiểu:
   `test_gemini_json_multitable_hierarchical_family_v1.py`,
   `test_gemini_json_multitable_hierarchical_indexed_wiring_v1.py`,
   `test_gemini_json_multitable_hierarchical_repair_v1.py`,
   `test_source_observation_mapping_contract_v1.py` và
   `test_source_observation_lane_math_v1.py`.
5. Chạy diagnostic mới trên full271; materialize census/coverage/residuals.
6. Rà từng `N`, `U`, source-only, duplicate và equation violation trên selected
   JSON; với trường hợp quyết định, mở render/PDF-visible evidence.
7. Sinh PDF residual audit cho full271 và common204; kiểm mọi document đều có
   đúng một terminal disposition và mọi visible mappable row đều được sở hữu.
8. Chạy authoritative full271/common204 vào SQLite/store mới.
9. Kiểm counts, unique IDs, source/config hashes, projection, observation
   coverage, no-left-behind, tamper tests và restore/replay từ receipt.
10. Viết ledger full271, ghi rõ genuine `U`, test counts, artifact hashes và
    shared pins; chỉ lúc đó mới đánh dấu terminal.

Lệnh nền sau restore:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/unit/test_gemini_json_multitable_hierarchical_family_v1.py \
  tests/unit/test_gemini_json_multitable_hierarchical_indexed_wiring_v1.py \
  tests/unit/test_gemini_json_multitable_hierarchical_repair_v1.py \
  tests/unit/test_source_observation_mapping_contract_v1.py \
  tests/unit/test_source_observation_lane_math_v1.py
.venv/bin/ruff check src scripts tests
```

Không chạy toàn bộ `pytest` trước khi corpus/store đã khôi phục và hash gate đạt;
focused tests cho đúng family giúp phát hiện lỗi restore nhanh hơn.

## 10. Thứ tự tiếp tục sau khi sang máy mới

1. Restore Git và S3, xác minh tất cả checksum theo phần 11–13.
2. Xác minh shared pins và chạy focused tests hiện hữu mà chưa sửa code.
3. **F39 trước:** sửa sáu blocker, vì code đã gần nhất và review contract đã rõ.
4. **F36 thứ hai:** cập nhật runner tests, chạy fresh diagnostics/residuals,
   authoritative runs và ledger.
5. **F37 thứ ba:** rebuild census/PDF audits sau ID reseal, authoritative `v4`
   và ledger.
6. Chạy regression rộng qua F16–F40, xác minh ledger/store projection.
7. Chỉ mở Family 41 khi F36/F37/F39 đều terminal và checkpoint mới đã backup.

## 11. Git checkpoint và restore

### Receipt Git

| Trường | Giá trị |
| --- | --- |
| Branch | `codex/27-bank-2025-current` |
| Commit chứa toàn bộ code/test/evidence | `7b2e33d900d6d10fe6e339cd31847b8a86707060` |
| SHA-256 của canonical commit object đó | `1602d976774b403d8f718f7bd72b607144424d6e9f13efbe04e465f672bdcb37` |
| Push remote | `origin` → `https://github.com/lvlamduy/bctc_convert.git` |
| Git bundle S3 object/key | `bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/project/bctc-ai-27-bank-final.bundle` |
| Git bundle SHA-256 | xem `migration-manifest-final.json` cùng prefix |
| Output Vertex-Flex tự chứa | `bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/project/output-vertex-flex.tar.gz` |
| Output archive SHA-256 | `e6f3da3b1f62c2ba6fe82c807c5afec1157444dfc98ed39d664eccaf3adca9e9` |
| Final branch tip sau receipt commit | xem `source_git.final_branch_tip` trong `migration-manifest-final.json` |

Restore ưu tiên từ Git remote:

```bash
git clone https://github.com/lvlamduy/bctc_convert.git bctc-ai
cd bctc-ai
git switch codex/27-bank-2025-current
git pull --ff-only
git rev-parse HEAD
git status --short
```

`git rev-parse HEAD` phải bằng `source_git.final_branch_tip` trong manifest S3
và status phải sạch trước khi hydrate artifact. Commit code nền
`7b2e33d900d6d10fe6e339cd31847b8a86707060` phải là ancestor. Nếu GitHub không
truy cập được, lấy Git bundle từ S3, kiểm SHA-256 theo manifest, rồi clone/fetch
từ bundle vào một thư mục mới. Không `reset --hard` một checkout có dữ liệu
chưa kiểm kê.

Không dùng `backup_incremental_project_checkpoint.py --path output` cho lần
migration này. Snapshot cha lịch sử dưới đây từng chứa các object
PPOCR/VietOCR/geometry/DeepSeek/Gemma đã được người dùng yêu cầu purge; một
checkpoint mới bind cha đó sẽ không còn tự chứa và sẽ tái-catalog artifact cũ.
Thay vào đó migration dùng GitHub + Git bundle trực tiếp + archive `output/`
Vertex-Flex + hai corpus/archive database tự chứa.

Parent production sau chỉ giữ giá trị lịch sử/forensic, **không còn là restore
authority đầy đủ sau purge**:

- parent manifest key:
  `bctc-ai/snapshots/20260806T050030130746Z-4a469fab2334/manifest-74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b.json`;
- parent manifest SHA-256:
  `74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b`;
- parent run-record key:
  `bctc-ai/runs/20260806T050030130746Z-4a469fab2334/run-24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04.json`;
- parent run-record SHA-256:
  `24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04`.

## 12. S3 artifact checkpoint và restore

Bucket được phép là private `s3://test-s3-duylv/bctc-ai/`, region
`us-east-1`; versioning bật, public access bị chặn và server-side encryption là
AES-256. Không đưa AWS credentials vào Git, manifest hoặc tài liệu này.

### Receipt upload và download-verify

| Asset | S3 key | SHA-256 ciphertext/archive | Byte count | Version/verification |
| --- | --- | --- | ---: | --- |
| Git/project `output/` Vertex-Flex | `.../project/output-vertex-flex.tar.gz` | `e6f3da3b1f62c2ba6fe82c807c5afec1157444dfc98ed39d664eccaf3adca9e9` | `112223558` | tải-ngược hash exact; VersionId `FqNPGGslG7LmoxOtn5SuRf7zS9Ti7tH1` |
| `/dev/shm` Gemini/database/family evidence, đã loại stack OCR/model cũ | `.../artifacts/dev-shm-gemini-only-artifacts-v2.tar.gz` | `f5667816e4c32d474dc3e76ad6058fe1636b8b3632ecb3a6ae09a6a341c5c776` | `5535288695` | tải-ngược hash exact; VersionId `t_EHKoO7IfLoawCnuZG87s8mIZwjFQsJ` |
| Corpus old140 `/tmp/gemini-json-first-corpus-production-v2` | `.../artifacts/legacy-corpus-production-v2.tar.gz` | `3976577973ea467edf83197679cf3312309909ec3d8292a4e1fbaaffbe009e25` | `2029250577` | tải-ngược hash exact; VersionId `yr3QYiEz7SZKV17LXS.NbVInWerHa5zf` |
| Inventory 341 database/sidecar | `.../inventory/database-inventory.json` | `8797c10fe2ef79438888547da34adb18079f42aaf6afedaf8127279e71e6e915` | 25.834.647.552 source byte được inventory | tải-ngược hash exact; VersionId `Hkddu0Bv99MVgSANycJbN5xhZNoiav4J` |
| Integrity receipt bốn DB authority | `.../inventory/critical-database-integrity.json` | `7a4eb99382f660aa43bc11f7350cfd14e8043186d83c816b211d96d3d2df0bc7` | 4 DB | mọi `quick_check=ok`, FK=0; VersionId `qaJr8MTW0rDKZ2bM020nqifIPz3hrHk_` |
| Current Codex session encrypted | `.../codex/codex-current-session.jsonl.gz.gpg` | `2ea0d53cbcd33fc19b83b90b0f1808cc040c08151305778528c9e6a64d281e8b` | `1982152606` | decrypt lại đúng 5.135.334.922 byte/plain SHA; VersionId `vQLMGDHbkoprARhaiztzpBWkhOWZ4gqy` |
| Tail của current Codex session | `.../codex/codex-current-session-tail-5135334922-5136683449.jsonl.gz.gpg` | `302e2d7f68f4a0344d37074b39fea1cd580886590feb2c27b19891bca732f12f` | `474490` | decrypt đúng 1.348.527 byte, nối ngay sau base; VersionId `FOfUnGu22UJfm8l522fmVFjBT.vNrXR3` |
| Các Codex session/config/state an toàn khác | `.../codex/codex-other-sessions-support.tar.gz.gpg` | `762b6a7d61c0e1bd7a837fb6cd9e00f7b5a7b59afc9181763a3f0db3d253f112` | `4626317224` | decrypt/list 1.041 member; không auth/current; VersionId `FL9_mzbmDhx4oAfggq7bahTvDY3MIcYX` |
| Receipt purge OCR/model cũ | `.../inventory/s3-obsolete-purge-receipts.tar.gz` | `b36efc6629df68257c3049f719260d6cec03c6db51689edd63655df86794a032` | `9216991` | 38.244 exact versions deleted; VersionId `sY01GIrsdjxWNelSVvQeAvJZDsych.hB` |
| Coverage PDF nguồn | `.../source/source-pdf-coverage-manifest.json` | `7e1c35cc26873477a53157754991a123ae2fc5fc2405470c7ba23c45980e5a35` | `8361` | 1.013 PDF/8.405.358.934 byte, 0 thiếu; VersionId `dsXgarGk3Uh9XPE8JXe_VHk9RuXoIYiQ` |
| Migration manifest tổng | `.../manifest/migration-manifest-final.json` | xem companion `.sha256` cùng prefix | xem manifest | download-verify bắt buộc |

Mọi đường dẫn bắt đầu bằng `.../` trong bảng trên dùng prefix đầy đủ
`s3://test-s3-duylv/bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/`.

PDF nguồn không được upload trùng thành một archive 7,55 GB. Gate dedup đã băm
toàn bộ 1.013 PDF hiện hành: 996 logical path khớp byte với 959 content object
độc nhất trong snapshot `20260806T050030130746Z-4a469fab2334`; sau purge tất
cả vẫn hiện diện, không thiếu/không lệch size. Ba PDF VPB mới đã có sẵn dưới
content-addressed key và được tải ngược/băm lại. Chỉ đúng 14 PDF còn thiếu
(138.013.340 byte) được PUT mới dưới `.../source/vietstock_bctc/...`; từng file
đã tải ngược và khớp SHA-256. Danh sách delta ở
`.../source/source-pdf-delta.tsv`, SHA-256
`3c2366d2cf87057282a10b9ea00a52a63b7d0e65914bd71a7d146e5f7ccb4e01`,
VersionId `yMSgXGvtF8Fe7_0jb_ojXZfxOL0BQKBw`. Manifest coverage nêu trên bind
toàn bộ ba nhóm, logical path, size, SHA và VersionId; dùng nó để hydrate đúng
1.013 PDF. Ba file acquisition hỗ trợ chưa có trên S3 cũng được PUT riêng;
compiled `__pycache__` bị loại có chủ đích.

Yêu cầu acceptance cho mỗi archive ngoài project tool:

1. ghi exact source root, archive format, byte count và SHA-256;
2. upload với SSE AES256 vào key mới dưới
   `s3://test-s3-duylv/bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/`;
3. đọc object metadata/version;
4. stream tải ngược object và tính lại SHA-256;
5. so khớp exact hash trước khi cho phép xóa máy;
6. test list/extract vào thư mục trống, ít nhất với manifest và sample JSON,
   SQLite, PNG/render và script tạm.

Các pattern loại khỏi archive `/dev/shm` và khỏi restore là `ppocr`, `vietocr`,
`geometry`/`geomety`, `deepseek`, `gemma`, và `paddleocr` (không phân biệt hoa
thường). Việc xóa S3 chỉ thực hiện sau khi liệt kê exact key và kiểm tra object
content-addressed không còn được manifest Gemini/database hợp lệ tham chiếu.
Receipt xóa S3: object `inventory/s3-obsolete-purge-receipts.tar.gz`, SHA-256
`b36efc6629df68257c3049f719260d6cec03c6db51689edd63655df86794a032`.
Nó chứng minh 38.244 cặp exact `Key+VersionId` (1.595.439.363 byte) bị xóa
vĩnh viễn, target còn lại bằng 0, 11 object dùng chung và 8 object database
không thiếu/không drift. File inventory PaddleOCR còn trên S3 chỉ là receipt,
không phải model/data runtime.

Trên máy mới, tải archive vào filesystem đủ dung lượng, kiểm ciphertext/archive
SHA trước khi giải nén. Nếu đủ RAM, khôi phục `/dev/shm` đúng layout cũ để các
command/receipt có absolute path tiếp tục chạy. Nếu không đủ, extract vào ổ SSD
riêng và truyền root/index/store paths bằng CLI; không sửa nội dung immutable
manifest chỉ để đổi đường dẫn vật lý.

Sau extract phải kiểm ít nhất:

```bash
sha256sum \
  /dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json \
  /dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json
```

Sau đó mở SQLite read-only, đếm lại document/page records và chạy corpus
validation trước family replay. Không gọi provider khi file thiếu; thiếu artifact
là lỗi restore, không phải quyền tái-extract.

## 13. Khôi phục phiên Codex

Phiên đang làm việc có ID:
`019fda51-7114-7573-918c-849ce79d78e1`.

File nguồn trên máy cũ:
`/root/.codex/sessions/2026/08/07/rollout-2026-08-07T03-43-18-019fda51-7114-7573-918c-849ce79d78e1.jsonl`.
File append-only này khoảng 5,13 GB trước khi snapshot; exact byte boundary và
plaintext SHA phải lấy từ migration manifest, không lấy kích thước ước lượng ở
đây.

Archive session phải mã hóa client-side (ví dụ GPG symmetric AES-256) trước khi
đưa lên S3 private, vì transcript lịch sử có thể chứa credential đã từng được
dán vào chat. Passphrase không được lưu trong Git, S3 cùng archive, shell history
hoặc tài liệu này. Receipt:

- exact plaintext byte count: `5135334922`;
- plaintext slice SHA-256:
  `f5be2f5206c20a071da6009c06bdaefe1aa4bc2f05ed12b3844088749cba1905`;
- ciphertext key:
  `bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/codex/codex-current-session.jsonl.gz.gpg`;
- ciphertext SHA-256:
  `2ea0d53cbcd33fc19b83b90b0f1808cc040c08151305778528c9e6a64d281e8b`;
- tail ciphertext key:
  `bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/codex/codex-current-session-tail-5135334922-5136683449.jsonl.gz.gpg`;
- tail ciphertext SHA-256:
  `302e2d7f68f4a0344d37074b39fea1cd580886590feb2c27b19891bca732f12f`;
- tail plaintext bắt đầu tại offset `5135334922`, dài `1348527` byte, SHA-256
  `c69cbff7a4b21735167be58f78bc057bde80e5ec15392c8a9aabb9a0dd41617a`;
- sau khi nối base và tail, prefix phiên có đúng `5136683449` byte và SHA-256
  `be05b4c116020df4b02a920d5b297410ef1a6d4d65fe3e0291eb5f1b27161f03`;
- cipher/compression: `gzip -1` rồi GPG symmetric `AES256`, sau đó S3 SSE
  `AES256`;
- passphrase location ngoài băng:
  được giao trực tiếp cho người dùng trong câu trả lời cuối của phiên migration;
  không nằm trong Git hay S3.

Trên máy mới:

1. Cài Codex CLI và đăng nhập mới bằng `codex login`; không backup/restore
   `~/.codex/auth.json`.
2. Tải cả base ciphertext và tail ciphertext, kiểm riêng SHA-256 của từng
   object. Giải mã/giải nén base, sau đó giải mã/giải nén tail và nối đúng một
   lần vào cuối base. Không đảo thứ tự và không chèn newline.
3. Kiểm file sau nối có đúng `5136683449` byte và SHA-256
   `be05b4c116020df4b02a920d5b297410ef1a6d4d65fe3e0291eb5f1b27161f03`,
   rồi đặt file vào đúng relative path
   `~/.codex/sessions/2026/08/07/rollout-2026-08-07T03-43-18-019fda51-7114-7573-918c-849ce79d78e1.jsonl`
   với quyền chỉ user đọc/ghi.
4. Mở terminal tại checkout Git đã xác minh và chạy:

```bash
codex resume 019fda51-7114-7573-918c-849ce79d78e1
```

Nếu giao diện đang mở, có thể dùng `/resume`. Dù resume transcript thành công,
Codex mới vẫn phải đọc tài liệu này trước khi sửa code vì filesystem/artifact
state không được suy ra chỉ từ lịch sử chat.

Không sao chép các path nhạy cảm sau vào backup dự án hoặc session-config
archive: `~/.codex/auth.json`, `~/.aws`, `~/.ssh`, Git credential store,
`.env`, token/key plaintext. Đăng nhập lại trên máy mới. Các session backup V1
lịch sử ngày 2026-08-07 đang security-quarantined vì chứa GitHub credential;
không dùng chúng làm bản phục hồi được chấp nhận.

## 14. Checklist trước khi xóa máy cũ

- [ ] Không còn process pytest/runner/provider/replay đang chạy.
- [ ] Tất cả file Git, kể cả untracked test/config/ledger, đã qua secret scan.
- [ ] `git diff --check` đạt; JSON mới/sửa parse được.
- [ ] `git add -A`, commit và push branch thành công.
- [ ] Clone/fetch hoặc `git ls-remote` xác minh remote chứa exact commit.
- [ ] Git bundle self-contained và archive `output/` tải ngược, hash exact;
      không chạy incremental checkpoint bind parent snapshot cũ.
- [ ] `/dev/shm` archive tải ngược và SHA khớp.
- [ ] old140 archive tải ngược và SHA khớp.
- [ ] Source-PDF coverage manifest đạt 1.013/1.013; restore đủ ba nhóm parent,
      content-addressed mới và 14-file migration delta, không tải lại OCR/model.
- [ ] Database-only archive tải ngược, SHA khớp và sample SQLite `quick_check`
      đạt; full271/common204 store hiện diện đúng path.
- [ ] S3 đã xóa vĩnh viễn đúng 38.244 cặp `Key+VersionId` PPOCR6/VietOCR/
      geometry/DeepSeek/Gemma/PaddleOCR đã kiểm kê; post-delete receipt xác nhận
      còn 0 target và 11 shared + 8 database object được bảo toàn.
- [ ] Current Codex session ciphertext tải ngược và SHA khớp.
- [ ] Passphrase session đã lưu ngoài máy cũ và ngoài S3 archive.
- [ ] Migration manifest tổng có đầy đủ key/hash/byte/version ID.
- [ ] Ít nhất một restore thử vào thư mục trống đã mở được Git bundle, JSON,
      SQLite và một render/PDF evidence.
- [ ] Người dùng đã nhận exact commit, S3 prefix, manifest hash, session ID và
      passphrase/location của passphrase.

Chỉ khi mọi ô trên đạt mới xem máy cũ là có thể xóa. Không xóa local artifact
chỉ dựa trên việc bucket là private; tính toàn vẹn phải được chứng minh bằng
download-and-rehash.

## 15. Lệnh mở đầu cho phiên Codex mới

Sau khi restore, gửi yêu cầu sau cho Codex mới:

> Đọc toàn bộ
> `docs/operations/MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md`, xác minh commit,
> S3 restore receipts, hai shared-file SHA và corpus indexes. Không gọi provider.
> Chạy focused tests hiện hữu trước khi sửa code. Tiếp tục F39 bằng sáu blocker
> đã ghi; sau khi F39 terminal mới đóng F36 rồi F37. Không mở Family 41 và không
> sửa hai shared frozen files.

Đây là điểm tiếp tục an toàn; diagnostic cũ được giữ để điều tra nhưng không có
quyền tự nâng thành release.
