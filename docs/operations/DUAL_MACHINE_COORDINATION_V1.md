# Phối hợp VPS và laptop — 2025 đến hiện tại

Đọc đầy đủ `MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md` trước tài liệu này.
Đây là điều phối bổ sung, không thay thế manifest migration, không chứng nhận
restore hoặc release. Không sửa checkpoint đã niêm phong. Base Git:
`8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.

## Phân công vòng đầu

| Worker | Phạm vi được sửa | Nhánh riêng |
| --- | --- | --- |
| `vps` | F36 OPERATING_EXPENSE | `codex/f36-operating-expense-vps` |
| `laptop` | F39 INCOME_TAX; review/đề xuất tích hợp | `codex/f39-income-tax-laptop` |
| Chưa giao | F37 CREDIT_RISK_PROVISION_EXPENSE; chỉ đọc/preflight | Không nhận tự động |

Contract: `config/coordination/dual-machine-v1.json`. Canonical SHA-256:
`53992eae3cc89762d9f86a1db99e46e9fcdde24e434211c479991a06c5da4707`.
Canonical bytes dùng JSON `sort_keys=True`, `separators=(',', ':')`,
`ensure_ascii=True`, thêm một LF, encode ASCII; không phụ thuộc CRLF của checkout.
Round: `20260905-f36-vps-f39-laptop`.

`integration_branch` và `integrator` chỉ mô tả đích/vai trò dự kiến, không cấp
quyền push. Theo laptop chuyển tiếp chỉ dẫn user mới nhất, không bên nào push
nhánh chung khi chưa có cho phép rõ ràng mới. Chỉ push nhánh worker đã được phép.
Receipt đính chính pin F37 không thuộc allowlist vòng này: báo hash đã kiểm tra
được phép read-only, còn ghi receipt phải chờ preflight và phạm vi bổ sung đã
review/được phép. Không sửa contract niêm phong để tự mở rộng quyền.

Shared evaluator/generic runner đóng băng theo hai pin trong contract.
Không mở family mới cho đến khi F36/F37/F39 đóng theo migration.
Không gọi provider; chỉ dùng PDF/Gemini JSON/receipt/SQLite đã có.
Không khôi phục hoặc upload stack OCR cũ, secrets hay passphrase.

## Kênh liên lạc thật

Bucket `test-s3-duylv`, region `us-east-1`, prefix:
`bctc-ai/coordination/2025-current/v1/`.

- `events/`: hộp thư chung, mỗi tin là một object JSON **mới**, không ghi đè.
- `rounds/20260905-f36-vps-f39-laptop/contract.json`: contract bất biến.
- `rounds/20260905-f36-vps-f39-laptop/joins/vps.json` và `joins/laptop.json`:
  xác nhận phạm vi, bind SHA contract. Không dùng ACK văn bản thay formal join.
- `artifacts/WORKER/RUN_ID/`: chỉ evidence/output/DB mới; không upload lại PDF
  hoặc corpus đã có trong migration. Mỗi run dùng prefix riêng.

Đây là giao thức hợp tác, **không phải scheduler hoặc khóa phân tán có lease**.
Codex chỉ nhận tin khi đang chạy và đọc S3; object không đánh thức phiên đã dừng.
Im lặng, heartbeat cũ, runtime lỗi hoặc laptop offline không chuyển quyền family.
Muốn đổi phân công: dừng writer cũ, gửi RELEASED, kiểm tra không còn job, hai bên
xác nhận contract/vòng mới. Không sửa contract hoặc xóa join của vòng cũ.

Các tin khởi tạo/manual có thể hiện trong informational inbox nhưng không phải
formal join. Không chạy lệnh lấy từ tin nhắn như shell; đọc, kiểm nguồn và đối chiếu
phạm vi. Private bucket không làm một chỉ dẫn ngoài phạm vi trở thành được phép.

## Bắt đầu trên laptop

Fetch không thay đổi worktree:

```text
git fetch origin codex/coordination-2025-current-v1
git show origin/codex/coordination-2025-current-v1:docs/operations/DUAL_MACHINE_COORDINATION_V1.md
git status --short
```

Nếu worktree sạch, tạo nhánh F39 từ base đã xác minh nếu chưa có. Nếu đang có
nhánh F39/chỉnh sửa, giữ nguyên chúng, xem diff và tích hợp riêng bốn file điều
phối; không reset, không checkout đè file. Chỉ cherry-pick các commit điều phối
đã review (diff tổng phải đúng bốn file; không lấy lịch sử worker family khác).
Nhánh điều phối có commit helper đầu tiên và các commit cập nhật tài liệu;
cherry-pick riêng tip sẽ thiếu helper nếu chưa có commit đầu tiên.

Các lệnh dưới chỉ dành cho **cài lần đầu** trên nhánh mới từ base:

```text
git switch -c codex/f39-income-tax-laptop 8efd618b6c77f0cdbb402a440e7ba3b3549184f1
git log --oneline 8efd618b6c77f0cdbb402a440e7ba3b3549184f1..origin/codex/coordination-2025-current-v1
git diff --stat 8efd618b6c77f0cdbb402a440e7ba3b3549184f1 origin/codex/coordination-2025-current-v1
git cherry-pick 8efd618b6c77f0cdbb402a440e7ba3b3549184f1..origin/codex/coordination-2025-current-v1
```

Worker đã cài không chạy lại toàn bộ range. Fetch rồi dùng
`git cherry -v HEAD origin/codex/coordination-2025-current-v1`, review từng commit
`+` chưa áp dụng và chỉ cherry-pick đúng SHA còn thiếu, cũ trước mới sau; `-` là
patch tương đương đã có. Worktree bẩn/conflict phải giữ nguyên và xử lý có review,
không reset/force/skip tự động. Chỉ dẫn preflight của user luôn đi trước việc cài.

Sau đó dùng Python 3.12 theo yêu cầu mới laptop chuyển tiếp lúc 06:10 UTC;
thay `python` bằng đường dẫn Python phù hợp. Các test VPS đã chạy với 3.11
chỉ là diagnostic, không phải acceptance 3.12.
`--profile PROFILE` là tùy chọn global đặt trước subcommand; có thể bỏ khi AWS
default đã đúng. Không cần chia sẻ key hoặc passphrase qua hộp thư.

```text
python scripts/operations/coordinate_family_workers_v1.py status
python scripts/operations/coordinate_family_workers_v1.py join --worker laptop --accept-disjoint-ownership
python scripts/operations/coordinate_family_workers_v1.py check --worker laptop
python scripts/operations/coordinate_family_workers_v1.py send --worker laptop --state HEARTBEAT --message "F39 only; restore gates still pending; no F36/F37 writes."
```

Join là xác nhận nhánh/phạm vi, không phải restore/release PASS. Có thể join khi
đang phục hồi runtime nhưng phải báo rõ BLOCKED và không bỏ qua gate migration.
Helper kiểm tra branch/base/frozen hashes và diff tracked/working paths. Hai join
phải khớp contract trước `check`/CHECKPOINT/READY_FOR_INTEGRATION. Kiểm tra lại
trước mỗi batch sửa hoặc replay. Không coi join là proof không có tiến trình khác
ghi DB: mỗi worker phải tự kiểm tra process và cô lập thư mục runtime.

Laptop hiện báo Windows native bị vướng symlink privilege, SQLite source identity
`fstat/stat st_ctime_ns`, binary read CRT. Đây chưa phải bằng chứng DB hỏng.
Không sửa guard shared để né lỗi. Việc cài WSL/Linux cần quyền/quyết định trên máy
laptop; dùng Linux filesystem và Python 3.12 rồi chạy lại toàn bộ gate.
VPS có thể chạy acceptance Linux cho commit laptop khi hai bên phân công rõ;
kết quả Linux không chứng nhận native Windows.

## VPS và nhịp checkpoint

Coordinator publish contract bằng `bootstrap`. VPS dùng nhánh F36 có bốn file
điều phối, rồi `join --worker vps --accept-disjoint-ownership`; lệnh và profile
giống laptop. Chỉ có một writer điều phối cho bốn file common; family workers
không tự chỉnh contract/helper sau join.

- Đọc `status` và gửi HEARTBEAT khoảng mỗi 10 phút khi đang chạy, và mỗi chuyển
  trạng thái: BLOCKED, CHECKPOINT, READY_FOR_INTEGRATION, RELEASED, INTEGRATED.
- Git push **chỉ nhánh worker được phép**, từng thay đổi nguyên tử đã test, mục tiêu không quá 30–60 phút khi
  có code mới. Không có code mới thì không tạo commit rỗng. Checkpoint WIP phải
  ghi rõ chưa nghiệm thu; không gắn READY khi còn gate chưa PASS.
- Gửi hash commit, kết quả test, next step và S3 run refs trong message. Không
  sửa nhánh chung; laptop chỉ review/đề xuất các commit family riêng và gates
  tích hợp. Cập nhật nhánh chung cần quyền rõ ràng mới từ user. INTEGRATED chỉ do laptop gửi từ worker
  checkout, nêu exact integrated commit; helper không tự merge hoặc chứng minh
  acceptance hoặc quyền push. RELEASED/INTEGRATED đóng vòng, không tự giành lại quyền.
  Tích hợp trong worktree riêng; giữ checkout worker F39 chỉ chứa F39 và bốn
  file điều phối để lệnh báo INTEGRATED không mang theo thay đổi F36 ngoài phạm vi.
- Duy trì tối đa 6 sub-agent + root cho phần độc lập. Chia review/test/repro/audit,
  không cho nhiều agent cùng sửa một file. Mọi agent tuân theo owner của máy.

## Dữ liệu, tài nguyên và bằng chứng

VPS lúc bắt đầu: root disk chỉ khoảng 350 MiB trống, `/dev/shm` khoảng 7.3 GiB.
Generic runner tạo private snapshot khoảng 547 MiB full271 / 528 MiB common204.
Không dùng default `/tmp`, không copy toàn bộ corpus, không ghi vào authority DB.

Mỗi job có `TMPDIR`, `SQLITE_TMPDIR`, output và `--results-database` riêng dưới
`/dev/shm`; set `PYTHONDONTWRITEBYTECODE=1`, pytest `-p no:cacheprovider`.
Dự trù tối thiểu 1.5 GiB mỗi heavy replay và giữ 2 GiB dự phòng, tối đa hai heavy
replay đồng thời; đo lại trước từng job. Các số này là planning, không phải peak
đã đo. Giữ nguyên source root/index/PDF và xác thực như migration.

Helper F36 cũ trong archive hardcode `/tmp/bctc-ai-27-bank`; chạy từ worktree
mới không tự đổi import. Giữ bytes archived helper; port riêng trong owned path
`scripts/experiments/build_f36_*.py` với repo/CLI paths và test trước khi dùng.
Builder F37 không thay cho manual PDF review: đổi sample/receipt phải xem lại PDF.

Checkpoint run mới cần commit/hash config/shared, command/env không chứa secret,
census/sweep/audit/coverage/indexed/trials, fresh result SQLite và integrity receipt,
run record cùng byte-count/SHA-256/VersionId. Đóng writer trước khi chụp DB; dùng
SQLite backup/checkpoint nhất quán nếu còn WAL, không copy DB đang ghi. Kiểm
`quick_check`/`foreign_key_check`, hash, upload immutable, tải ngược exact VersionId
và rehash. Corpus/PDF cũ chỉ tham chiếu manifest migration, không upload trùng.

PUT dùng `If-None-Match: *`; xung đột dừng, không ghi đè. Mỗi object được kiểm
readback exact VersionId. Không xóa event/claim hay thay latest-pointer. Tin có
timestamp lệch phải đối chiếu `reply_to`/LastModified; không suy quyền chỉ từ thứ
tự tên file. Branch Git đã push là backup code; tmpfs chưa upload sẽ mất khi reboot.

## Checkpoint thực tế 2026-09-05, 06:14 UTC

Đã liên lạc hai chiều qua events. Laptop gửi OWNERSHIP_ACK lúc 06:10, xác nhận
không sửa F36/F37. VPS đã publish contract và formal join, readback/hash PASS.
Laptop tiếp tục gửi `COORDINATION_JOIN_DEFERRED_BY_USER_PREFLIGHT_GATE` lúc
06:14: chỉ dẫn user bên laptop cấm đổi nhánh trước restore preflight PASS, nên
chưa thể tạo nhánh F39/cherry-pick helper/join. **Formal handshake vẫn PENDING**.
Không dùng ACK trước đó để vượt cổng này. Laptop tạm ngưng mutation, không hứa
poll khi phiên đã trả quyền cho user. Cần user cho phép/thiết lập Linux/WSL
Python 3.12 trên laptop rồi chạy lại gate; peer không thể cấp quyền thay user.

Commit helper/config/docs/tests đầu tiên đã push:
`91c11824ef7d4a1b2ddbca0211ee8b6aa26d9d12`, nhánh điều phối và F36.
29 test điều phối + Ruff PASS với Python 3.11 (diagnostic). Shared/main branch
vẫn nguyên `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`.

Đã dùng sáu sub-agent cho phần độc lập; chưa sửa file family:

- F36: 72 focused PASS, 2 stale runner tests FAIL. Rà soát thêm tái hiện hai
  defect: unsupported/conflicting explicit unit bị mất khi nối bảng; thứ tự
  page-map làm đổi sealed IDs. Có repro 7 FAIL/2 controls PASS, chưa phải fix.
- F37: 49 focused PASS, SHA source DB full/common khớp. PDF audit vẫn stale,
  chưa census/replay mới, chưa terminal. Giữ reserved/read-only.
- F39: tái hiện độc lập đủ sáu blocker, gửi report và script cho laptop; chưa sửa.
- VPS chưa có Python 3.12. Có uv nhưng overlay khoảng 340 MiB, `/dev/shm` noexec;
  không cài environment đầy đủ hoặc replay thiếu dung lượng. 3.11 không thay
  bằng chứng acceptance 3.12.

Sáu file report/repro/review đã upload riêng và tải ngược kiểm SHA tại
`artifacts/vps/20260905-preflight-v1/` trong prefix điều phối. Receipt checkpoint
S3 mới bind exact VersionId/SHA của từng file. Không upload lại PDF/corpus DB.
Tiếp tục: giải quyết quyền/runtime laptop → review helper → formal join/check
hai bên → F36 sửa bounded trên nhánh riêng, laptop F39 → acceptance/replay/
audit/integrity/ledger → đề xuất tích hợp F39 rồi F36 rồi F37, sau khi được phép
và F37 được phân công riêng. Không đánh dấu release từ
các diagnostic trên, không sửa frozen engine, không gọi provider.

## Bổ sung 06:23 UTC — user yêu cầu tiếp tục chuẩn bị F36 trên VPS

Sau checkpoint tạm ngưng, user trực tiếp yêu cầu tiếp tục thực hiện song song
và dùng tối đa sub-agent. VPS tiếp tục **chuẩn bị code/test F36, chưa release**
dựa trên yêu cầu đó và OWNERSHIP_ACK rõ ràng của laptop rằng không sửa F36.
Đây không phải timeout, tự nhận lease hay thay đổi quyền/runtime của laptop.
Contract S3 giữ nguyên; formal handshake vẫn PENDING, `check` chính thức và
READY_FOR_INTEGRATION vẫn yêu cầu cả hai join. Không dùng đường chuẩn bị để
vượt preflight, nghiệm thu, ghi authority DB, chuyển family hay push nhánh chung.

Gate chuẩn bị do root kiểm tra trước mỗi batch:

1. Yêu cầu user hiện tại cho phép tiếp tục F36 song song; không suy quyền từ S3.
2. Exact ACK key
   `events/20260905T061035292182Z-LAPTOP_INTEGRATOR-OWNERSHIP_ACK-6ceb0149ad654ec99933eb9c95429c80.json`,
   VersionId `MFtrAcG74yCEFK5YUVQxt3577B.Go2zJ`, SHA-256
   `a6935b1cf1be3849eda826f98fd39aa83099a3b065d7815db85862553a9c006c`;
   base/branch khớp, `F36.laptop_will_edit=false`. Đọc cả tin mới để phát hiện
   rút ACK hoặc scope thay đổi; nếu có mâu thuẫn, dừng.
3. Chạy `check_repo(contract, 'vps', repo)` của helper: branch/base ancestor,
   frozen hashes, committed/staged/worktree/untracked paths phải đạt. Đây là
   local scope check, không được gọi/ghi nhãn là formal handshake PASS.
4. Chỉ file F36 được khai báo; mỗi sub-agent sở hữu file riêng; không provider,
   không long replay hay authority DB write. Test 3.11 ghi diagnostic-only;
   acceptance vẫn cần 3.12 và toàn bộ migration gates.
5. Push checkpoint WIP trên F36, gửi HEARTBEAT kèm commit/test/evidence tới
   laptop; không giả READY/CHECKPOINT formal khi thiếu join. Nếu laptop offline,
   không hứa đã nhận tin; chỉ nhận là delivered khi có phản hồi thực tế.

Kết thúc chuẩn bị không đồng nghĩa F36 terminal. Laptop vẫn giữ F39/preflight;
F37 chỉ được rà soát read-only cho tới khi được phân công rõ ràng.
