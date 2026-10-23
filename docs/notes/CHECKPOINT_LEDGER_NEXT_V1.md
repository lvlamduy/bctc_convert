# Checkpoint ledger: `claude/tm-notes-next` (EXPERIMENTAL, UNSEALED)

Đây là nhánh pilot của Claude cho notes engine. Không có mục nào dưới đây là nghiệm thu tài chính, seal family hay tương đương với export production. Mọi lượt chạy đều là development diagnostic, chạy theo grant DECISIONS #10 do Codex cấp. Các lượt FAIL cũng được ghi lại đầy đủ.

## Commit (theo thứ tự, gốc là `1fc78cb` của `claude/tm-notes-engine`)

| Commit | Nội dung |
|---|---|
| `180dfde` | Nhãn khớp nhiều line trực tiếp vẫn là AMBIGUOUS dù bị lọc owner/not_within (Codex 0151/0152) |
| `91971b5` | F36 opt-in: owner của payroll đi qua đúng một wrapper GROUP "Trong đó" có mọi ô null (Codex 0150) |
| `6450be9` | Chỉ áp wrapper khi trục giá trị ORIGINAL đầy đủ: bảng đơn, EXACT, identity map (Codex 0155) |
| `c95743a` | Sắp lại thứ tự import (Codex 0157) |
| `c372c45` | Fixture dương của wrapper thỏa gate không đổi `min_emitted_lines` (Codex 0160) |
| `2752878` | Coverage `OBSERVED_UNRESOLVED`, `NOTES_COVERAGE_STATUS_V2` (Codex 0155/0157) |
| `2150a6f` | Tài liệu: `NOTES_ENGINE_ARCHITECTURE_REVIEW_V1.md` |

## Unit (`unit_only_v6/v7.sh`, AS 1,5 GiB)

| HEAD | Kết quả | terminal.json SHA |
|---|---|---|
| `220ea3c` (engine) | PASS 111/111 | `ea8a544e…4f674` |
| `1811e86` (engine) | PASS 116/116 | `da437bae…fb98` |
| `1fc78cb` (engine) | PASS 118/118 | `0d2f46f5…ecb0` |
| `c95743a` | **FAIL** 121/122. Fixture dương của wrapper chỉ có 2 line in ra; gate là đúng. | `75fffce1…06c9` |
| `c372c45` | PASS 122/122 | `daf501ba…0d50` |
| `2150a6f` | PASS 123/123 | `a491e5ed…f184` |

## FULL271 (6 family, PRIMARY store `00951257…`, launcher v7/v8)

| Lượt | HEAD | Kết quả | terminal / store |
|---|---|---|---|
| `153912Z` | `220ea3c` | PASS_DIAGNOSTIC: 31.080 cell, 0 bảng bị bridge từ chối | `8fc0392b…` / `bdc4e9a2…` |
| `161543Z` | `1fc78cb` | **FAILED** `interrupted=HUP@run`: shell Windows bị reap | `7251270a…` |
| `164023Z` | `1fc78cb` (root) | PASS_DIAGNOSTIC: 30.702 cell | `e6021611…` / `74843198…` |
| `194848Z` | `2150a6f` (root, v8 `df1f1380…`) | PASS_DIAGNOSTIC: 30.814 cell, wall 4:24.79, RSS 644 MB | `685ff1f9…` / `92dba9b9…` |

## Bằng chứng dẫn xuất (đọc artifact đã xong, không đụng DB/PDF nguồn)

- **`153912Z → 164023Z`**
  - comparator `83dda65f…`, tally `49fde93a…`.
  - OPEX ACCEPTED giảm 2.578 → 1.370: 145 dòng payroll không chứng minh được owner, nên phương trình INCOMPLETE.
  - F37: 12 bảng chuyển EVALUATED → `ONLY_1_LINES`, vì parent bị in hai lần.
  - Phát hiện một lỗi thật: nhãn ghép bị gỡ tính mơ hồ (sửa ở `180dfde`).
- **`164023Z → 194848Z`**
  - comparator `42c667cb…`, tally `8f59ce69…`.
  - 57 dòng payroll chuyển OWNER_NOT_PROVEN → MEMBER qua wrapper (domain `ORIGINAL_EXACT_UNSHIFTED_SINGLE_TABLE`; 56 qua r3, 1 qua r2), nên OPEX có thêm 114 cell AFTER_ONLY.
  - 292 cell HOLD → ACCEPTED và 5 cell HOLD → ACCEPTED_DASH, tất cả SAME_READING/SAME_RNID; 1.370 cell giữ ACCEPTED.
  - Dòng ghép `5517a8a0…/s1/t5/r4` trở lại AMBIGUOUS (2 cell BEFORE_ONLY).
  - F37: `changed_documents` rỗng; cả 34 document ở trạng thái OBSERVED_UNRESOLVED ở hai phía (cùng một luật áp cho cả hai lượt).
  - Năm family còn lại không đổi.

## COMMON204 (corpus riêng, ordinal riêng; không dùng lại ordinal của FULL271)

| Lượt | HEAD | Kết quả | terminal / store |
|---|---|---|---|
| PRIMARY `common204-20261023T201701Z` (root, `primary_common204_v2.sh` `ef3fa2ed…`) | PRIMARY `07eb7a5` | PASS: 204 result ID khớp chính xác; A 2:39, RSS 1,04 GB; B 1:21 | `d496a6a4…` / `35fde24a…` (215.445.504 B) |
| notes `common204-20261023T203411Z` (root, `common204_notes_v1.sh` `cb8f55fc…`) | notes `f03c5d2` | PASS_DIAGNOSTIC: 23.108 cell, 204 workbook, reload và rebuild khớp chính xác; wall 3:25.13; RSS 509 MB; 0 bảng bị REJECTED vì SOURCE_BRIDGE / PRIMARY_CONTEXT | `7b9804a3…` / `38299376…` |

Coverage của COMMON204, theo family (FOUND / OBSERVED_UNRESOLVED / NOT_OBSERVED):

- INCOME_TAX: 94 / 22 / 88
- OPERATING_EXPENSE: 196 / – / 8
- CREDIT_PROVISION_EXPENSE: 89 / 23 / 92
- CREDIT_QUALITY: 204 / – / 0
- DEPOSITS_BY_TYPE: 200 / – / 4
- BY_CUSTOMER_ENTITY_TYPE: 130 / – / 74

Đây là số đếm ở mức cell, mang tính thử nghiệm, không phải độ chính xác tài chính. So sánh FULL271 với COMMON204 cần một kế hoạch có kiểm identity riêng.

## Việc còn mở

- Luật marker gạch đầu dòng ("- ") cho leaf/label (43 dòng): cần kế hoạch đọc ORIGINAL được duyệt trước.
- So sánh pilot với F39 theo tọa độ ORIGINAL: chưa được duyệt.
- COMMON204: cần store PRIMARY COMMON204 khớp identity; không dùng lại ordinal của FULL271.
- Chưa mở family mới hay F41 khi F36/F37/F39 còn chưa terminal.
