# Unresolved mapping and adjudication review ledger

Updated: 2026-08-22 (UTC)

This is the cumulative human-readable file requested for every source item or
family region that could not initially be mapped.  Entries remain here after
resolution so the project owner can audit the original issue, the adjudication,
and the exact result that closed it.  `NO_COMPLETE_REGION` alone never means a
family is absent; report-level absence is recorded only when the project owner
explicitly confirms it for the bound PDF.

This is the single cross-family review file.  Every new unresolved entry records,
when applicable: family, bank, report and reporting period, exact PDF/page/region
locator, raw VietOCR Transformer text, accentless normalized text, independent
pixel transcription when they disagree, visible values and axes, nearest schema
candidate, accounting/structure checks that passed or failed, the unresolved
reason, and the next evidence needed.  Bank/report/page fields are evidence
locators only and are never parser or mapping conditions.

Ledger total: **441 entries**.  Current open queue: **221**.  Closed history:
**132** row/graph resolutions and **88** confirmed bound-report family absences.
Later families append here rather than creating disconnected candidate lists.
Bank/report/page fields below are evidence locators only, never matching rules.

## OPEN — family-first 140-filing `Chứng khoán kinh doanh`

The authenticated document-store sweep finds 114 filing-local topology regions:
36 are `VERIFIED_BY_CODEX`, 26 are bounded `NOT_OBSERVED_PROPOSAL_ONLY`, and 78
remain `UNRESOLVED_EVIDENCE_GATES`.  The 78 exact filing trials and source rows
are retained in
`output/calibration/family-first-accounting-evidence-sweeps-v1/trading-securities.json`;
the table below groups only identical open failure classes for readability.

| Bank | Filing/trang còn mở | Owner/khoản mục nguồn nhìn thấy | Lý do chưa map |
| --- | --- | --- | --- |
| ACB | annual/H1/Q1–Q4 2025 và H1/Q1/Q2 2026, p15–16, p41, p45–48 | `Chi tiết chứng khoán kinh doanh`; `Chứng khoán nợ/vốn`; issuer leaves; listed/unlisted view | 15 filing có ít nhất một hàng source thiếu ô của một kỳ; các bảng hai trang chưa chứng minh kế thừa kỳ/đơn vị. Không điền ô thiếu và không cộng issuer view với listed/unlisted view. |
| MBB | annual/H1/Q1–Q4 2025 và H1/Q1/Q2 2026, p27, p30, p38, p41, p48–52 | `Chứng khoán kinh doanh`; `Chứng khoán nợ/vốn`; issuer leaves; `Đã/Chưa niêm yết` | 12 filing: một số hàng thiếu lane; một số header có lane đơn vị không khớp body; annual/H1 hợp nhất chứa hai view cùng population nên subtotal không bằng union của mọi child nhìn thấy. |
| VPB | annual/H1/Q1–Q4 2025, p30–32, p37, p40, p43, p45 | `Chứng khoán kinh doanh`; issuer/listing children | 9 filing: hàng source thiếu lane; các bảng công ty mẹ có merged header hoặc continuation làm trục cột/kỳ/đơn vị chưa duy nhất; subtotal nợ thuộc một alternate view, không được dùng để đóng union hai view. |
| HDB | annual/H1/Q1–Q4 2025 và Q1/Q2 2026, p21–35 | `Chứng khoán kinh doanh`; `Chứng khoán Nợ/Vốn`; issuer/listing/provision leaves | Cả 16 filing có family nhưng còn mở. Bốn annual/H1 dùng header kỳ tương đối chưa xác thực identity; các quarter thiếu numeric lane hoặc merged header; Q2/2026 p24–25 còn lệch số lane unit/body và continuation chưa chứng minh. Cần refresh đúng các page/crop này, không quét lại corpus. |
| VCB | annual và Q4/2025, p29–31, p37–38 | `Chứng khoán kinh doanh`; issuer leaves | 3 filing: hàng source thiếu lane hoặc period header chưa phủ mọi cột; continuation annual/Q4 chưa có period/unit edge chắc. |
| CTG | annual/H1/Q1–Q4 2025 và H1/Q1/Q2 2026, p29, p33–45 | `Chứng khoán kinh doanh`; `Chứng khoán nợ/vốn`; issuer/listing leaves | 12 filing: merged/local header và incomplete lanes chiếm đa số; một số subtotal nợ/vốn không bằng population child vì alternate view; không ép closure bằng cách cộng hai view. |
| BID | annual/H1/Q1–Q4 2025 và Q1/Q2 2026, p19–41 | `Chứng khoán kinh doanh`; issuer/listing leaves | 11 filing: body-column/header chưa dựng duy nhất, nhiều hàng thiếu lane, hoặc period/unit continuation chưa được chứng minh. |

VIB không nằm trong queue này: cả 18 filing là bounded
`NOT_OBSERVED_PROPOSAL_ONLY` cho trading securities; các bảng AFS/HTM thuộc
`Chứng khoán đầu tư`.  Sáu filing riêng lẻ VPB và hai filing riêng lẻ CTG cũng
không quan sát thấy family trong đúng PDF đã bind.  Không kết luận rộng hơn các
filing này.

## CLOSED — family-first 140-filing `Tiền gửi tại NHNN`

The baseline formal replay scanned all 140 available filings. A bounded refresh
then authenticated and root-checked only the affected MBB document packet,
proved it was the only mixed-separator candidate inside this family's topology
regions, and produced 70 `VERIFIED_BY_CODEX`, 70
`NOT_OBSERVED_PROPOSAL_ONLY`, zero `UNRESOLVED` and 245 mappings.

| ID | Bank/report | Trang | Khoản mục nguồn và giá trị nhìn thấy | Kết quả đóng |
| --- | --- | ---: | --- | --- |
| FF-CBD-001 | MBB H1/2026 công ty mẹ | 39 | `Tiền gửi tại NHNNVN bằng VND (i)`: `19.849.504` / `55.307.732`; raw PP-OCRv6 comparative token `55,307.732`; sample `sample-000498485`; crop SHA `232a952a6707802818f1971ccbd785252fc61ee28375d4a1a44f27df419daa42` | `CLOSED`: giữ nguyên raw token, bảo toàn dãy chữ số thành candidate scale 0; VietOCR cùng crop đọc `55.307.732`, lane tiền có các peer scale 0 và `55.307.732 + 10.429.524 + 667.675 = 66.404.931` đóng chính xác. Gemma lặp lại dấu sai của PP-OCR nên không tham gia authority. |

Machine-readable authorities:
`output/calibration/family-first-topology-sweeps-v1/central-bank-deposits.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/central-bank-deposits-evidence.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/central-bank-deposits-mapping.json`
và receipt cùng thư mục.

## CLOSED — family-first 140-filing `Tiền, kim loại quý và đá quý`

The baseline formal replay scanned all 140 available filings. A bounded refresh
authenticated and root-checked only the two affected VIB document packets,
proved they were the complete mixed-separator scope inside this family's
topology regions, and produced 72 `VERIFIED_BY_CODEX`, 68
`NOT_OBSERVED_PROPOSAL_ONLY`, zero `UNRESOLVED` and 292 mappings.

| ID | Bank/report | Trang | Khoản mục nguồn và giá trị nhìn thấy | Kết quả đóng |
| --- | --- | ---: | --- | --- |
| FF-CASH-001 | VIB Q2/2025 hợp nhất | 32 | `Tiền mặt bằng VND`: `1.460.873` / `1.195.200`; raw PP-OCRv6 current token `1.460,873`; crop SHA `ef1eca9f1bb9cfb0c2494ad7bd1ad5c7b8e05054457cb3b9276ab9833fac49aa` | `CLOSED`: VietOCR cùng crop và hai request Gemma độc lập đọc `1.460.873`; lane tiền scale 0 và `1.460.873 + 382.482 + 94 = 1.843.449` đóng chính xác. |
| FF-CASH-002 | VIB Q2/2025 công ty mẹ | 31 | `Tiền mặt bằng VND`: `1.460.854` / `1.195.181`; raw PP-OCRv6 current token `1,460.854`; crop SHA `99ff5a40cacb70c9b4ca1c257a946ed8484400e8d51823c03013de1da462ca40` | `CLOSED`: VietOCR cùng crop và hai request Gemma độc lập đọc `1.460.854`; lane tiền scale 0 và `1.460.854 + 382.482 + 94 = 1.843.430` đóng chính xác. |

Machine-readable authorities:
`output/calibration/family-first-topology-sweeps-v1/cash-precious-metals.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/cash-precious-metals-evidence.json`,
`output/calibration/family-first-accounting-incremental-refresh-v1/cash-precious-metals-mapping.json`
và receipt cùng thư mục.

## CLOSED — annual-2025 `Chi phí dự phòng rủi ro tín dụng`

E-0144 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025. Graph chung
tìm đúng một note chi tiết tại ACB p70, MBB p75, VPB p73, VCB p61 và VIB p52;
pixel, trục số nguồn, schema hiện hành và 12 phương trình xác minh 25 mapping/50
ô số. Một dấu `-` hiện kỳ của VPB được crop-bind trước khi chuẩn hóa 0; không có
disagreement số VietOCR và không còn dòng OPEN. Các component `Dự phòng cho vay
giao dịch ký quỹ và ứng trước` + `Dự phòng cho tài sản Có khác có rủi ro` của
VPB, cũng như hai component dự phòng trái phiếu doanh nghiệp chưa niêm yết của
VCB, được xác minh riêng rồi cộng đúng một lần vào 1228 `Dự phòng khác`.

| ID | Bank | Locator/đối chứng | Disposition và căn cứ bounded absence |
| --- | --- | --- | --- |
| CRPE-A2025-001 | HDB | Toàn filing; aggregate tại KQKD/báo cáo bộ phận và diễn giải chính sách | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết 1221 với trục kỳ, đơn vị, các hàng thành phần và tổng; aggregate không được relabel thành bảng chi tiết. |
| CRPE-A2025-002 | CTG | p60 chi phí hoạt động + aggregate KQKD | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: `Chi phí dự phòng` là nhãn chung trong family chi phí hoạt động, không phải note chi tiết rủi ro tín dụng 1221. |
| CRPE-A2025-003 | BID | p57 chi phí hoạt động + aggregate KQKD | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: dòng `(Hoàn nhập) dự phòng` tại p57 loại trừ dự phòng rủi ro tín dụng/chứng khoán; không có note chi tiết 1221 ở nơi khác trong filing. |

Các kết luận trên chỉ là vắng mặt trong đúng filing annual-2025 đã bind, không
phải khẳng định bank/source rộng hơn. Machine-readable result:
`docs/experiments/E-0144-annual-2025-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập, chi phí và lãi thuần từ hoạt động khác`

E-0145 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p69, MBB p74, VPB p71, HDB p51, VCB p60, CTG p59,
BID p56 và VIB p51. Pixel, trục số nguồn, schema hiện hành và 48 phương trình
xác minh 72 mapping/144 ô số; không có disagreement số VietOCR, family absence
hoặc dòng OPEN.

Graph chung nhận tổng có/không có nhãn, số đứng trước nhãn theo provider order,
child tùy chọn và các cách gọi `hoán đổi lãi suất`, `giao dịch phái sinh`, `nợ
xấu/cho vay đã xử lý`, `nghiệp vụ bán nợ`. Các dòng phạt hợp đồng, kinh doanh
khác, tài trợ khác hoặc `Khác` được đưa vào catch-all tương ứng chỉ bằng phép
cộng có kiểm soát trên từng số nguồn đã xác minh; parent thu, parent chi và net
đều phải đóng. Không tạo unresolved candidate mới và không dùng bank/page làm
điều kiện matching.

Machine-readable result:
`docs/experiments/E-0145-annual-2025-other-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập nhân viên của ngân hàng`

E-0149 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p73, VPB p73, BID p58 và VIB p54. Pixel, trục số nguồn,
schema hiện hành và 16 phương trình xác minh 18 mapping/36 ô số. MBB, HDB, VCB
và CTG là bounded detailed-note absences trong đúng filing đã bind.

Không còn dòng OPEN. BID được nhận bằng biến thể từ vựng tổng quát cho `cán bộ,
nhân viên bình quân`; VIB giữ topology số đứng trước nhãn. Hai số bình quân năm
ACB được kiểm tra ngược với quỹ lương/tổng thu nhập chia số nhân viên, rồi mới
quy đổi 12 tháng sang 1267/1268; OCR không được dùng làm numeric truth.

Machine-readable result:
`docs/experiments/E-0149-annual-2025-employee-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Tình hình thực hiện nghĩa vụ với ngân sách nhà nước`

E-0150 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p73, MBB p68, VPB p64, HDB p47, VCB p65, CTG p62,
BID p52 và VIB p52. Pixel, trục số nguồn, schema hiện hành và 35 phương trình
xác minh 35 mapping/140 ô logic; không có family absence hoặc dòng OPEN.

Các biến thể nhiều block, cột phải trả/ứng trước, nhánh phải thu/phải trả và
nhãn quấn dòng đều được xử lý bằng graph chung. CTG chỉ net các ô phải thu/phải
trả sau khi từng thành phần được xác thực. Dấu `-` HDB được bind pixel rồi mới
chuẩn hóa 0; numeric challenger bác lỗi VietOCR `80.055` và giữ số nguồn
`60.055`. Không có khoản mục nào cần đưa vào ledger OPEN.

Machine-readable result:
`docs/experiments/E-0150-annual-2025-state-budget-obligations-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ`

E-0151 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025. Graph chung
tìm đúng một vùng customer-scoped tại ACB p74, VPB p74, HDB p54 và VIB p54;
pixel, trục số nguồn, schema hiện hành và 10 phương trình xác minh 25 mapping/50
ô số. ACB giữ dòng `GTCG do doanh nghiệp phát hành` như chi tiết không cộng lặp;
VIB cộng bốn dòng nguồn đã xác thực đúng một lần vào 1288 `Khác`.

HDB dùng trục tương đối `Số cuối năm`/`Số đầu năm`. Crop nguồn bác proposal
VietOCR `368.639.341` và xác nhận `388.639.341`; chỉ số nguồn này mới làm tổng
so sánh `706.190.899` đóng chính xác. Không còn dòng OPEN.

| ID | Bank | Locator/đối chứng | Disposition và căn cứ bounded absence |
| --- | --- | --- | --- |
| CC-A2025-001 | MBB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết customer-collateral 1280–1288 với owner, hai trục và các hàng thành phần; policy/credit-risk mentions không được relabel. |
| CC-A2025-002 | VCB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có vùng customer-scoped thỏa graph đầy đủ; tài sản của chính ngân hàng và diễn giải bảo đảm là đối chứng âm. |
| CC-A2025-003 | CTG | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết 1280–1288 với period/unit/numeric topology trong filing annual đã bind. |
| CC-A2025-004 | BID | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có note chi tiết 1280–1288; các mention chính sách/hạn mức không mang bảng thành phần khách hàng. |

Các kết luận trên chỉ là vắng mặt trong đúng filing annual-2025 đã bind, không
phải khẳng định bank/source rộng hơn. Machine-readable result:
`docs/experiments/E-0151-annual-2025-customer-collateral-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Tài sản/GTCG ngân hàng đưa đi thế chấp, cầm cố và chiết khấu`

E-0152 quét đủ 695 trang và tìm đúng một vùng bank-owned tại ACB p74, MBB p78,
VPB p74, CTG p63 và VIB p54. Graph chung cho phép owner + một child khi hai kỳ,
đơn vị và ô số cùng đóng topology; vì vậy bảng MBB một hàng không còn bị loại
bởi ngưỡng hai child cũ. Nhãn quấn dòng CTG, các child trực tiếp ACB và các hàng
GTCG/repo tổng quát đều đi qua cùng matcher, không dùng bank/page để route.

Pixel, trục số nguồn, schema hiện hành và 10 phương trình xác minh 13 mapping/26
ô số. Hai dash ACB và một dash CTG chỉ thành 0 sau khi crop render được xác thực.
Các hàng nguồn tổng quát tại MBB/VPB/CTG/VIB được cộng đúng một lần vào 1293
`Tài sản khác`; không thu hẹp ngầm sang 1290/1291. Không còn dòng annual OPEN.

| ID | Bank | Locator/đối chứng | Disposition và căn cứ bounded absence |
| --- | --- | --- | --- |
| BPA-A2025-001 | HDB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có owner bank-owned cùng ít nhất một child, hai kỳ và đơn vị; customer collateral/policy không được relabel. |
| BPA-A2025-002 | VCB | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có bảng 1289–1293 chi tiết thỏa graph trong filing đã bind. |
| BPA-A2025-003 | BID | Toàn filing | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`: không có vùng bank-owned pledged/discounted-assets đủ topology; các mention vay/bảo đảm không phải bảng family. |

Ba kết luận này chỉ là bounded absence trong đúng filing annual-2025. Các dòng
BPA-001–BPA-003 của lượt hiện hành E-0097 vẫn OPEN theo đúng source/hierarchy
cũ và không bị kết quả annual relabel. Machine-readable result:
`docs/experiments/E-0152-annual-2025-bank-pledged-assets-8bank-codex-verified-mapping-v1.json`.

## OPEN/CLOSED — annual-2025 `Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra`

E-0153 quét đủ 695 trang và tìm đúng một vùng value-bearing tại ACB p75,
MBB p79, VPB p75, HDB p55, CTG p63, BID p59 và VIB p55. VCB p66 chỉ có
diễn giải family; p67 đã sang note giao dịch bên liên quan, nên đây là một
bounded detailed-table absence trong đúng filing annual đã bind. Pixel, trục số
nguồn, schema hiện hành và 46 phương trình xác minh 58 mapping/114 ô số.

HDB dùng hai parent trung gian và tiền ký quỹ âm; BID dùng group bảo lãnh cùng
group cam kết thanh toán; VIB map cột thuần sau khi gross và ký quỹ đóng đúng.
Tất cả 15 ReportNormId hiện có của family đều đã được dùng nơi nguồn hỗ trợ.
Các source row sau vẫn OPEN vì source có độ chi tiết/trục khấu trừ mà schema
không có. Chúng tái diễn đúng các gap CL-001–CL-005/CL-007–CL-014 của lượt hiện
hành, nên ledger giữ cùng ID thay vì tạo 13 schema-gap ID trùng nghĩa.

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| CL-001 | ACB | 75 | Cam kết trong nghiệp vụ L/C trả ngay | `3.393.925` / `1.999.681` | Parent 1295 chưa có leaf L/C trả ngay. |
| CL-002 | ACB | 75 | Cam kết trong nghiệp vụ L/C trả chậm | `3.531.929` / `1.519.333` | Parent 1295 chưa có leaf L/C trả chậm. |
| CL-003 | ACB | 75 | Trừ: Tiền ký quỹ — L/C | `(259.375)` / `(207.241)` | Đây là trục khấu trừ để ra L/C thuần, không phải schema value hiện có. |
| CL-004 | ACB | 75 | Bảo lãnh khác — dòng con | `11.804.589` / `7.752.095` | Dòng con lặp tên group parent; map thêm vào 1300 sẽ double-count. |
| CL-005 | ACB | 75 | Trừ: Tiền ký quỹ — bảo lãnh | `(1.459.157)` / `(1.068.032)` | Đây là trục khấu trừ để ra bảo lãnh thuần, chưa có leaf schema. |
| CL-007 | VPB | 75 | Trừ: Tiền ký quỹ — L/C | `(387.745)` / `(57.332)` | Trục khấu trừ đóng parent L/C nhưng chưa có leaf schema. |
| CL-008 | VPB | 75 | Cam kết bảo lãnh khác | `25.861.416` / `9.932.865` | Child lặp nghĩa group `Bảo lãnh khác`; không map hai lần vào 1300. |
| CL-009 | VPB | 75 | Trừ: Tiền ký quỹ — bảo lãnh | `(1.959.457)` / `(671.675)` | Trục khấu trừ đóng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-010 | VPB | 75 | Hoán đổi lãi suất tiền tệ chéo — nhận | `46.229.090` / `35.324.065` | Chưa có leaf nhận của swap lãi suất tiền tệ chéo. |
| CL-011 | VPB | 75 | Hoán đổi lãi suất tiền tệ chéo — trả | `46.716.751` / `36.760.922` | Chưa có leaf trả của swap lãi suất tiền tệ chéo. |
| CL-012 | VPB | 75 | Hoán đổi lãi suất một đồng tiền | `24.343.737` / `39.136.588` | Chưa có leaf swap lãi suất một đồng tiền. |
| CL-013 | VPB | 75 | Cam kết khác — dòng con | `296.447.263` / `229.654.799` | Child lặp tên parent 1304; map thêm sẽ double-count. |
| CL-014 | VPB | 75 | Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang | `294.728.542` / `229.511.446` | Dòng `Trong đó` non-additive chưa có leaf schema. |

Machine-readable result:
`docs/experiments/E-0153-annual-2025-contingent-liabilities-8bank-codex-verified-mapping-v1.json`.

## OPEN/CLOSED — annual-2025 `Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý`

E-0154 quét đủ 695 trang và tìm đúng hai bảng đồng thời có nhánh giá trị ghi
sổ và giá trị hợp lý tại VPB p94 và VCB p73–74. Pixel toàn trang, trục số
nguồn, schema hiện hành và 9 phương trình xác minh 41 mapping/35 ô số. Hai
trang bảng landscape được xử lý trực tiếp trong hệ tọa độ upright canonical;
không xoay về portrait và không chiếu bbox ngược vào logic dựng bảng.

ACB chỉ có diễn giải rằng chưa xác định giá trị hợp lý. MBB/BID chỉ có bảng
phái sinh; HDB/VIB chỉ có nội dung rủi ro tín dụng; CTG có bảng rủi ro tiền tệ.
Đó là sáu bounded detailed-table absences trong đúng filing annual-2025, không
phải khẳng định source-wide rằng bank không có công cụ tài chính.

Hai gap nguồn tái diễn đúng FI-001/FI-002 của lượt hiện hành nên không tạo ID
schema-gap trùng nghĩa:

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Giá trị | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| FI-001 | VPB | 94 | Giá trị hợp lý của phần lớn tài sản và nợ tài chính | `(*)` | Nguồn ghi chưa xác định được giá trị hợp lý; ký hiệu không phải 0 và giá trị ghi sổ không được dùng thay thế. |
| FI-002 | VCB | 74 | Giá trị hợp lý của phần lớn tài sản và nợ phải trả tài chính | `(*)` | Nguồn ghi không thể ước tính đáng tin cậy và không thuyết minh giá trị số; giữ OPEN. |

Machine-readable result:
`docs/experiments/E-0154-annual-2025-financial-instruments-8bank-codex-verified-mapping-v1.json`.

## OPEN/CLOSED — annual-2025 `Rủi ro tiền tệ`

E-0155 quét toàn bộ 695 trang và tìm đúng một bảng hiện kỳ tại ACB p84,
MBB p97, VPB p88, HDB p63, VCB p80, CTG p71, BID p65 và VIB p71. Bốn bảng
so sánh tại ACB p85, MBB p98, CTG p72 và VIB p72 được nhận diện nhưng không
được dùng thay cho kỳ báo cáo. Pixel, trục số nguồn, schema hiện hành và 74
phương trình xác minh 155 mapping/155 ô số; tám dấu `-` được xác thực trước
khi chuẩn hóa thành 0. Không có residual trình bày ở các mapping đã nhận.

Gemma 4 local GPU cứu hộ đúng hai nhãn BID mà VietOCR Transformer sai
chính tả: `Trạng thái tiền tệ nội bảng` và `Trạng thái tiền tệ ngoại bảng`.
Một full-page control làm sai chữ số nên Gemma chỉ có text-diagnostic
authority trên hai crop đó, tuyệt đối không có numeric authority.

Bảy nhóm sau vẫn OPEN/source-only. Đây là khoảng trống schema, không phải lỗi
OCR hay hình học; các giá trị của chúng vẫn được giữ đầy đủ để đóng các tổng
nguồn và không bị gộp ngầm sang một trục tiền tệ khác.

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| A2025-CRISK-001 | ACB | 84 | AUD | Không có trục AUD tương đương dưới family 1352–1482. |
| A2025-CRISK-002 | ACB | 84 | CAD | Không có trục CAD tương đương dưới family 1352–1482. |
| A2025-CRISK-003 | ACB | 84 | JPY | Không có trục JPY tương đương dưới family 1352–1482. |
| A2025-CRISK-004 | ACB | 84 | Vàng | Schema chưa có nhánh trục vàng. |
| A2025-CRISK-005 | VPB | 88 | Vàng | Schema chưa có nhánh trục vàng. |
| A2025-CRISK-006 | HDB | 63 | Vàng | Schema chưa có nhánh trục vàng. |
| A2025-CRISK-007 | CTG | 71 | Vàng | Schema chưa có nhánh trục vàng. |

Machine-readable result:
`docs/experiments/E-0155-annual-2025-currency-risk-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Rủi ro lãi suất`

E-0156 quét toàn bộ 695 trang và tìm đúng một vùng hiện kỳ tại ACB p87,
MBB p95, VPB p85, HDB p65, VCB p78, CTG p75, BID p67 và VIB p68. Bốn bảng
so sánh ACB p88, MBB p96, CTG p76 và VIB p69 được giữ làm control. Header
CTG gộp text `Quá hạn`/`Không chịu lãi`, nhưng x-centre của các hàng số xác
thực hai cột độc lập. Exact replay xác minh 280 mapping/280 ô, 87 phương
trình và 10 DASH→0 có pixel component.

Chỉ còn một nhóm OPEN. Đây là residual nguồn, không phải lỗi OCR/header:

| ID | Bank | Trang annual-2025 | Khoản mục nguồn | Giá trị và lý do chưa map |
| --- | --- | ---: | --- | --- |
| AIRRISK-001 | VPB | 85 | Tổng cộng — tổng tài sản, tổng nợ, trạng thái nội bảng/ngoại bảng/kết hợp | `1.277.980.310 - 1.079.873.967 = 198.106.343`; ngoại bảng `2`; nội + ngoại = `198.106.345`, nhưng kết hợp in `198.106.343`. Giữ nguyên cả 5 ô, residual 2 và không tự sửa/làm tròn. |

Machine-readable result:
`docs/experiments/E-0156-annual-2025-interest-rate-risk-8bank-codex-verified-mapping-v1.json`.

## COMPLETE — annual-2025 `Mua mới và thanh lý các công ty con`

E-0148 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và không tìm
thấy vùng nào có đủ ba dòng bắt buộc 1256–1258. Tất cả 25 hit gần là policy,
narrative mua/bán/hợp nhất công ty con hoặc caption dòng tiền; không hit nào có
đủ tổng giá trị, tiền thanh toán và tiền thực có trong đơn vị được mua/thanh lý.
Kết quả là 8 bounded-report absences, 0 mapping và 0 dòng OPEN.

Machine-readable result:
`docs/experiments/E-0148-annual-2025-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json`.

## COMPLETE — annual-2025 `Tiền và các khoản tương đương tiền`

E-0147 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p73, MBB p78, VPB p73, HDB p54, VCB p64, CTG p62,
BID p58 và VIB p50. Pixel, trục số nguồn, schema hiện hành và 18 phương trình
xác minh 43 mapping/86 ô số. Ba dấu `-` nhìn thấy được bind trước khi chuẩn hóa
zero. Không có family absence, disagreement số hay dòng OPEN mới.

Machine-readable result:
`docs/experiments/E-0147-annual-2025-cash-equivalents-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Chi phí thuế thu nhập doanh nghiệp`

E-0146 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng thuế chi tiết tại ACB p71, MBB p76, VPB p64, HDB p52, VCB p62,
CTG p60, BID p57 và VIB p53. Pixel, trục số nguồn, schema hiện hành và 32
phương trình xác minh 61 mapping/120 ô số. Không có family absence. Hai proposal
số VietOCR sai được giữ nguyên và bị numeric challenger bác bỏ: CTG
`(370.109]` → `(370.109)` và VIB `2.40i` → `2.401`; không sửa tay số nguồn.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| A2025-ITAX-ACB-001 | ACB | 71 | Các khoản điều chỉnh làm tăng/(giảm) thu nhập chịu thuế khác | `31.324` / `(145.520)` | Nhãn rộng; không ép vào một leaf điều chỉnh thuế cụ thể. |
| A2025-ITAX-ACB-002 | ACB | 71 | Hoàn nhập tài sản thuế TNDN hoãn lại | `14.913` / `33.594` | Schema có net thuế hoãn lại nhưng chưa có leaf component nguồn này; dòng vẫn tham gia phương trình net. |
| A2025-ITAX-ACB-003 | ACB | 71 | Chênh lệch tạm thời được khấu trừ | `(14.858)` / `(17.190)` | Schema có net thuế hoãn lại nhưng chưa có leaf component nguồn này; dòng vẫn tham gia phương trình net. |
| A2025-ITAX-MBB-001 | MBB | 76 | Thuế TNDN do thoái vốn tại công ty con | `(341.855)` / `BLANK` | Chưa có leaf thuế hiện hành do thoái vốn; ô so sánh để trống và không đổi thành 0. |
| A2025-ITAX-VPB-001 | VPB | 64 | Các điều chỉnh khác | `45.695` / `BLANK` | Dòng thuộc phần cuốn chiếu thuế phải nộp sau chi phí thuế, chưa có leaf chi phí tương đương; ô so sánh giữ trống. |
| A2025-ITAX-CTG-001 | CTG | 60 | Điều chỉnh khác | `1.396` / `(61.403)` | Dòng thuộc phần cuốn chiếu thuế phải nộp, không ép vào family chi phí thuế. |
| A2025-ITAX-VIB-001 | VIB | 53 | Điều chỉnh khác | `163` / `169` | Nhãn rộng hơn leaf 5733 về điều chỉnh thuế các năm trước; giữ source-only nhưng dùng trong phương trình tổng đã xác minh. |

Machine-readable result:
`docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Chi phí quản lý chung (Chi phí hoạt động)`

E-0143 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p70, MBB p74, VPB p72, HDB p51, VCB p61, CTG p60,
BID p57 và VIB p52. Pixel, trục số nguồn, schema hiện hành và 42 phương trình
xác minh 103 mapping/206 ô số. Bốn disagreement số của VietOCR được giữ nguyên
trong evidence và bị source/pixel/accounting bác bỏ: HDB `11.960.755` →
`11.980.755`, CTG `7.127.165` → `1.127.165`, CTG `75.588` → `15.588`, VIB
`804 696` → `804.696`. Dấu `-` hiện kỳ VCB được bind trước khi chuẩn hóa 0.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| OE-A2025-001 | ACB | 70 | Chi khác (dưới `Chi về tài sản`) | `1.222.510` / `1.212.164` | Schema không có leaf chi phí tài sản khác; không thu hẹp vào chi phí quản lý khác. |
| OE-A2025-002 | ACB | 70 | Hoàn nhập chi phí dự phòng (tổng) | `(3.362)` / `(16.637)` | Aggregate của hai component 1218/1220 đã map; giữ source-only để kiểm tra và tránh double count. |
| OE-A2025-003 | MBB | 74 | Chi khác về tài sản | `1.870.772` / `1.532.145` | Schema không có leaf chi phí tài sản khác. |
| OE-A2025-004 | VPB | 72 | Chi thuê tài sản | `1.009.205` / `924.119` | Schema không có leaf chi phí thuê tài sản dưới 1212. |
| OE-A2025-005 | VPB | 72 | Chi phí công nghệ thông tin | `1.275.072` / `928.944` | Schema không có leaf chi phí CNTT. |
| OE-A2025-006 | VPB | 72 | Chi về thuế GTGT đầu vào không được khấu trừ | `150.526` / `134.629` | Schema không có leaf VAT đầu vào không khấu trừ. |
| OE-A2025-007 | HDB | 51 | Chi thuê tài sản | `520.137` / `510.494` | Schema không có leaf chi phí thuê tài sản. |
| OE-A2025-008 | HDB | 51 | Chi về bảo dưỡng và sửa chữa tài sản | `372.394` / `300.759` | Schema không có leaf bảo dưỡng/sửa chữa tài sản. |
| OE-A2025-009 | HDB | 51 | Chi khác về tài sản | `134.640` / `155.665` | Schema không có leaf chi phí tài sản khác. |
| OE-A2025-010 | HDB | 51 | Chi phí quảng cáo, tiếp thị, khuyến mại | `812.322` / `857.690` | Schema không có leaf quảng cáo/tiếp thị/khuyến mại. |
| OE-A2025-011 | HDB | 51 | Chi phí hội nghị, lễ tân, khánh tiết | `232.505` / `458.607` | Schema không có leaf hội nghị/lễ tân/khánh tiết. |
| OE-A2025-012 | HDB | 51 | Chi phí điện, nước, vệ sinh cơ quan | `160.138` / `141.194` | Schema không có leaf tiện ích/vệ sinh cơ quan. |
| OE-A2025-013 | CTG | 60 | Chi khác (dưới `Chi về tài sản`) | `2.016.938` / `1.845.093` | Schema không có leaf chi phí tài sản khác. |
| OE-A2025-014 | CTG | 60 | Chi phí dự phòng | `161.178` / `427.692` | Nhãn nguồn chung không đủ căn cứ thu hẹp vào 1218 hoặc 1220. |

Machine-readable result:
`docs/experiments/E-0143-annual-2025-operating-expense-8bank-codex-verified-mapping-v1.json`.

## OPEN/CLOSED — annual-2025 `Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức`

E-0142 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng
một note chi tiết tại ACB p69, MBB p74, VPB p71, HDB p51, VCB p60, CTG p59 và
BID p56. Pixel, trục số nguồn, schema hiện hành và 20 phương trình xác minh 28
mapping/56 ô số; bốn dấu `-` được crop-bind trước khi chuẩn hóa 0 và không có
disagreement số VietOCR. VIB chỉ in aggregate ở báo cáo kết quả hoạt động p11;
toàn filing không có note chi tiết nên tạo một bounded absence.

Graph chung bổ sung ba biến thể ngữ nghĩa, không có bank/page rule: `Thu từ cổ
tức, lợi tức`; lãi bán hoặc thu nhập thanh lý khoản góp vốn/mua cổ phần; và
`Từ chứng khoán vốn`. BID chứng minh nhãn con có thể xuống dòng với hai giá trị
xen giữa hai fragment. Matcher hiện hành E-0087 vẫn giữ nguyên scan ID và replay
byte-exact.

### CCDI-CTG-001 — CTG — dòng chứng khoán vốn gộp

- Report: BCTC hợp nhất kiểm toán năm 2025.
- Physical page / family: 59 / thu nhập từ góp vốn, mua cổ phần và cổ tức.
- Source label / accentless: `Từ chứng khoán vốn` / `tu chung khoan von`.
- Visible values: `15.823 | 13.284` (`2025 | 2024`, triệu đồng).
- Nearest schema: ReportNormId 1200 `Từ chứng khoán Vốn kinh doanh` và 1201
  `Từ chứng khoán Vốn đầu tư`.
- Review status: `OPEN_NEEDS_SCHEMA_DECISION`.
- Reason: một số in gộp hai phạm vi mà schema hiện tách riêng; không có nguồn
  phân rã để chia số hoặc chọn một leaf. Dòng được xác minh source-only và cùng
  1202 đóng `15.823 + 55.529 = 71.352` / `13.284 + 7.255 = 20.539`.

Machine-readable result:
`docs/experiments/E-0142-annual-2025-capital-contribution-dividend-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư`

E-0141 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và không tìm
thấy dòng số tổng hợp ReportNormId 5990 trong bất kỳ filing nào: 0 complete
numeric row, 1 near control, 8 bounded absences và 0 dòng OPEN.

BID p56 in một tiêu đề mục chung `Lãi thuần từ mua bán chứng khoán kinh doanh và
chứng khoán đầu tư`, rồi trình bày hai bảng độc lập 30.1 trading và 30.2
investment. Pixel và hình học xác nhận tiêu đề không có hai giá trị cùng hàng;
hai bảng con không bị cộng để tạo một dòng schema không được in. Matcher dùng
cụm mở đầu lãi/(lỗ) thuần cùng đủ hai family anchors và cho phép từ nối `mua
bán`/`và`, nhưng vẫn yêu cầu số cùng hàng để trở thành complete region. ACB,
MBB, VPB, HDB, VCB, CTG và VIB không có cả near lẫn complete match. Kết luận chỉ
có authority trong tám báo cáo annual-2025 đã bind.

Machine-readable result:
`docs/experiments/E-0141-annual-2025-combined-securities-net-8bank-bound-report-absence-v1.json`.

## CLOSED — annual-2025 `Lãi/lỗ thuần từ mua bán chứng khoán đầu tư`

E-0140 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p68, MBB p73, VPB p70, HDB p50, VCB p59, CTG p59,
BID p56 và VIB p51. Exact replay xác minh 32 mapping/64 ô logic từ 70 thành
phần nguồn cùng 16 phương trình; không có dòng OPEN, family absence hoặc
disagreement số VietOCR.

Một graph chung nhận net có/không có nhãn, owner con dưới umbrella trading +
investment và nhánh dự phòng tùy chọn. VPB/VIB in nhiều hàng dự phòng AFS/HTM;
mỗi thành phần được pixel/source-challenge trước khi cộng đúng một lần vào 1196.
VCB không in dự phòng nên đóng `thu + chi = net`. Năm dấu `-` tại ACB/VPB/VIB
được khóa bằng crop trước khi chuẩn hóa 0. Không có bank/page rule mới.

Machine-readable result:
`docs/experiments/E-0140-annual-2025-investment-securities-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh`

E-0139 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p68, MBB p73, VPB p70, HDB p50, VCB p59, CTG p58 và
BID p56. Exact replay xác minh 27 mapping/54 ô số cùng 14 phương trình; không
có dòng OPEN hoặc disagreement số VietOCR.

Graph dùng chung cho phép net có/không có nhãn, nhãn dự phòng xuống dòng, owner
trading nằm dưới umbrella trading + investment và hàng dự phòng là tùy chọn.
HDB không in dự phòng nên `thu + chi = net`; sáu vùng còn lại đóng `thu + chi +
dự phòng = net`. VIB không có graph trading trong toàn filing; note mua bán
chứng khoán đầu tư là đối chứng family khác và tạo đúng một confirmed
bound-report absence, không tạo mapping giả.

Machine-readable result:
`docs/experiments/E-0139-annual-2025-trading-securities-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối`

E-0138 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p68, MBB p73, VPB p69, HDB p50, VCB p59, CTG p58,
BID p55 và VIB p51. Exact replay xác minh 69 mapping/138 ô logic từ 152 thành
phần nguồn cùng 48 phương trình; không có dòng OPEN hoặc family absence.

Graph dùng chung nhận tổng thu/chi đứng trước, đứng sau hoặc được suy ra từ
children; nhánh vàng tùy chọn; ngoại tệ giao ngay và vàng có thể tách hoặc gộp.
VCB cộng đúng một lần các thành phần bán/đánh giá lại vàng và giao dịch/đánh giá
lại phái sinh. ACB suy ra hai parent không in giá trị từ các child rồi đối chiếu
net. MBB được nhận qua owner, siblings, trục kỳ, đơn vị và accounting closure dù
nhãn gộp không có `giao ngay`. Năm dấu `-` nhìn thấy ở VCB/BID được xác thực từ
crop trước khi chuẩn hóa thành 0; các ô không phải DASH không có disagreement số
VietOCR.

Machine-readable result:
`docs/experiments/E-0138-annual-2025-fx-gold-activity-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Thu nhập, chi phí và lãi thuần từ hoạt động dịch vụ`

E-0137 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một vùng family tại ACB p67, MBB p72, VPB p69, HDB p50, VCB p58, CTG p58,
BID p55 và VIB p50. Exact replay xác minh 101 mapping/202 ô giá trị cùng 48
phương trình. Hai hàng gộp của CTG vẫn tham gia chính xác vào tổng thu/tổng chi
nhưng không được tách hoặc thu hẹp vào một leaf schema đơn lẻ.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| SA-CTG-001 | CTG | 58 | Thu từ dịch vụ tư vấn, ủy thác và đại lý | `965.390` / `961.413` | Một số nguồn gộp tư vấn với ủy thác/đại lý; schema hiện chỉ có các leaf tách rời 5986 và 1163, không có căn cứ phân bổ. |
| SA-CTG-002 | CTG | 58 | Chi về dịch vụ tư vấn, ủy thác và đại lý | `(309.758)` / `(195.158)` | Một số nguồn gộp tư vấn với ủy thác/đại lý; schema hiện chỉ có các leaf tách rời 5987 và 1172, không có căn cứ phân bổ. |

Hai disagreement số của VietOCR được giữ làm evidence, không tạo thêm OPEN:
HDB đọc thiếu ngoặc mở `73.409)` nhưng pixel/source là `(73.409)`; VIB đọc
`993 178` nhưng pixel/source là `993.178`. Numeric challenger và sáu phương
trình mỗi bank giữ đúng giá trị nguồn.

Machine-readable result:
`docs/experiments/E-0137-annual-2025-service-activity-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập từ lãi thuần`

E-0136 quét đủ 695 trang của tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng
một graph báo cáo kết quả hoạt động hợp nhất tại ACB p10, MBB p13, VPB p12,
HDB p10, VCB p11, CTG p11, BID p12 và VIB p11. Exact replay xác minh 8
mapping/16 ô giá trị cùng 48 đối chiếu statement–TM–công thức; không có dòng
OPEN hoặc family absence.

Hai cách gọi `Thu nhập lãi thuần` và `Thu nhập từ lãi thuần` cùng bind vào
ReportNormId 5985. VIB có provider order đặt hai giá trị trước nhãn nhưng
geometry vẫn bind đúng hàng. Mỗi giá trị statement được đối chiếu lại với
family 1143/1151 đã xác minh và phương trình live-schema `5985 = 1143 + 1151`;
VietOCR không được dùng làm numeric truth.

Machine-readable result:
`docs/experiments/E-0136-annual-2025-net-interest-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Chi phí lãi và các khoản tương tự chi phí lãi`

E-0135 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p67, MBB p72, VPB p68, HDB p49, VCB p58, CTG p57, BID p55 và
VIB p50. Exact replay xác minh 40 mapping/80 ô giá trị cùng 16 phương trình;
không có dòng OPEN hoặc family absence.

CTG dùng hai nhãn nguồn rút gọn `Lãi tiền gửi` và `Lãi tiền vay`; matcher chỉ
nhận chúng trong graph chi phí lãi đầy đủ, không nhận bằng chuỗi độc lập. HDB
VietOCR đọc `26,150.925`, còn pixel/trục số nguồn đọc `26.150.925`; cả hai
chuẩn hóa về 26.150.925 nên không phát sinh numeric disagreement. ReportNormId
1155 `Trả lãi tiền thuê tài chính` được ghi nhận không quan sát thấy trong tám
vùng đã bind, không phải tuyên bố vắng mặt toàn PDF.

Machine-readable result:
`docs/experiments/E-0135-annual-2025-interest-expense-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Thu nhập lãi và các khoản thu nhập tương tự`

E-0134 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p67, MBB p72, VPB p68, HDB p49, VCB p57, CTG p57, BID p54 và
VIB p50. Exact replay xác minh 55 mapping/110 ô giá trị cùng 28 phương trình;
không có dòng OPEN hoặc family absence.

Hai khoảng trống schema thực sự khác bản chất đã được đóng bằng append-only
ReportNormId 6075 `Thu nhập lãi cho vay khách hàng và các TCTD khác` cho dòng
gộp của MBB và 6076 `Thu phí nghiệp vụ thư tín dụng (L/C)` cho HDB. Các ID cũ,
giá trị và trạng thái mapping trước đó không đổi. Không có lỗi numeric cần
Gemma/rescue trong family annual này.

Machine-readable result:
`docs/experiments/E-0134-annual-2025-interest-income-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Các khoản phải trả và công nợ khác`

E-0132 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng một vùng
family tại ACB p64, MBB p67, VPB p63, HDB p47, VCB p54, CTG p54, BID p52 và
VIB p48. Exact replay xác minh 53 mapping/184 thành phần giá trị cùng 32 phương
trình; ba ô DASH của MBB/CTG được bind pixel trước khi chuẩn hóa 0. Không còn
dòng OPEN: mọi nhãn nguồn không có leaf chuyên biệt được map vào 1127 `Khác`,
giữ nguyên thành phần nguồn và đánh dấu non-additive với parent để không cộng
lặp. HDB fresh VietOCR đọc `14.169.816`; pixel, PP-OCRv6 và phương trình nguồn
xác nhận đúng là `4.169.816`.

E-0132A áp dụng cùng quyết định của chủ dự án cho lượt hiện hành E-0077 và đóng
OPL-001–OPL-018 vào 1127 `Khác`, không đổi số nguồn hay tái phân bổ parent.

Machine-readable results:
`docs/experiments/E-0132-annual-2025-other-payables-liabilities-8bank-codex-verified-mapping-v1.json`
và
`docs/experiments/E-0132A-other-payables-project-owner-other-closure-v1.json`.

## OPEN — annual-2025 `Vốn và các quỹ`

E-0133 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p65–66, MBB p69–70, VPB p66–67, HDB p48–49, VCB p56–57,
CTG p55–56, BID p53–54 và VIB p49–50; 23 vùng gần giống được giữ làm đối
chứng âm. Xoay toàn trang rồi detect lại CTG/BID/VIB trong tọa độ landscape
chuẩn giúp cả tám bảng xác minh 74 mapping/132 ô giá trị cùng 18 phương trình.
BID dùng word boxes để tách hai số chung một line. HDB fresh VietOCR đọc
`835.956`; pixel, PP-OCRv6 và phương trình nguồn xác nhận đúng là `535.956`.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị mở/đóng kỳ | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| A2025-CAF-001 | VPB | 66 | Quỹ đầu tư phát triển | `68.758` / `68.758` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| A2025-CAF-002 | HDB | 48 | Cổ phiếu quỹ | `(413.448)` / ô trống | Schema chưa có leaf số dư vốn tương đương; ô đóng kỳ trống không được đổi thành 0. |
| A2025-CAF-003 | HDB | 48 | Vốn đầu tư xây dựng cơ bản | `89` / `89` | Schema chưa có leaf số dư vốn tương đương. |
| A2025-CAF-004 | VCB | 56 | Quỹ đầu tư phát triển | `1.357.643` / `9.058.060` | Schema chưa có leaf riêng; hai số vẫn nằm trong subtotal quỹ và tổng vốn đã xác minh. |
| A2025-CAF-005 | CTG | 55 | Quỹ đầu tư phát triển | `512.455` / `548.467` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| A2025-CAF-006 | BID | 53 | Quỹ đầu tư phát triển | `290.036` / `6.903.598` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |
| A2025-CAF-007 | VIB | 49 | Quỹ đầu tư phát triển | `10.556` / `10.556` | Schema chưa có leaf số dư vốn tương đương; hai số vẫn nằm trong tổng vốn đã xác minh. |

Machine-readable result:
`docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Phát hành giấy tờ có giá`

E-0131 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p63, MBB p66, VPB p62, HDB p46, VCB p54, CTG p53–54, BID p52
và VIB p47. Exact replay xác minh 70 mapping/188 thành phần giá trị cùng 34
phương trình. Mười một ô DASH của CTG/VIB được bind pixel rồi mới chuẩn hóa 0.
Năm dòng dưới đây vẫn nằm trong parent/tổng nguồn nhưng không được phân bổ hoặc
ép sang một leaf sai nghĩa.

| ID | Bank | Trang | Khoản mục nguồn | Giá trị 2025 / 2024 | Lý do chưa map |
| --- | --- | ---: | --- | --- | --- |
| A2025-IVP-001 | VPB | 62 | Toàn family — Dưới 12 tháng | `25.699.521` / `53.256.694` | Trục kỳ hạn áp dụng cho tổng chứng chỉ tiền gửi và trái phiếu; không có phân bổ theo công cụ. |
| A2025-IVP-002 | VPB | 62 | Toàn family — Từ 12 tháng đến dưới 5 năm | `72.134.379` / `12.723.428` | Cùng trục toàn-family; không tự chia vào các leaf CD/kỳ phiếu/trái phiếu. |
| A2025-IVP-003 | VPB | 62 | Toàn family — Từ 5 năm trở lên | `9.286.753` / `995.582` | Cùng trục toàn-family; không tự chia vào các leaf theo công cụ. |
| A2025-IVP-004 | HDB | 46 | Chi phí phát hành | `(74.995)` / `(35.706)` | Dòng contra đã tham gia chính xác vào tổng giá trị thuần nhưng schema chưa có leaf chi phí phát hành riêng. |
| A2025-IVP-005 | VCB | 54 | Trung, dài hạn bằng ngoại tệ | `14` / `14` | Một số nguồn gộp hai bucket trung và dài hạn; không có căn cứ phân bổ sang 1115/1116. |

Tổng đầu năm HDB trên pixel là `81.349.744`; fresh VietOCR đọc nhầm
`31.349.744`, còn PP-OCRv6 và phương trình tổng đều xác nhận chữ số đầu là 8.

Machine-readable result:
`docs/experiments/E-0131-annual-2025-issued-valuable-papers-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Tiền gửi của khách hàng`

E-0129 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng một vùng
family tại mỗi bank và xác minh 159 mapping cùng 43 phương trình. Hai dòng gộp
của BID p51 dưới đây vẫn tham gia tổng nguồn nhưng không được tách số in sang
các leaf pháp lý riêng.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| A2025-CD-001 | BID | 51 | Công ty cổ phần (`204.344.052`) | Dòng nguồn không phân biệt công ty cổ phần vốn Nhà nước trên 50% (1081) và công ty cổ phần khác (1082). |
| A2025-CD-002 | BID | 51 | Doanh nghiệp tư nhân, cá nhân (`1.109.262.426`) | Một số in gộp doanh nghiệp tư nhân (1083) và cá nhân (1089), không có căn cứ phân bổ. |

Machine-readable result:
`docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Vốn nhận tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro`

E-0130 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại ACB p63, MBB p66, VPB p62, HDB p45, VCB p53, CTG p53, BID p51 và
VIB p47. Exact replay xác minh 20 mapping/40 ô giá trị cùng 8 phương trình;
không phát sinh dòng OPEN. Matcher được nới theo cấu trúc chung, không theo bank:
owner có thể không kèm số note nếu đã có child + hai kỳ + hai đơn vị + ô số, và
dòng child có thể bắt đầu bằng `Vốn tài trợ` thay vì chỉ `Vốn nhận`.

BID `bằng vàng và ngoại tệ` được giữ nguyên một số nguồn rồi map một lần vào
1099 `Khác`, không thu hẹp giả thành ngoại tệ. Dấu `-` hiện kỳ của VCB được
bind bằng crop render xác thực trước khi chuẩn hóa thành 0.

Machine-readable result:
`docs/experiments/E-0130-annual-2025-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json`.

## CLOSED — annual-2025 `Các khoản nợ Chính phủ và Ngân hàng Nhà nước`

E-0128 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025, tìm đúng một vùng
family tại mỗi bank. Sau adjudication của chủ dự án, exact replay xác minh 47
mapping/101 ô giá trị cùng 46 phương trình và không còn dòng OPEN. Sáu dấu `-`
được bind trực tiếp vào crop ảnh rồi chuẩn hóa 0; số so sánh `1` của HDB cũng
được bind bằng crop số vì detector không sinh một line/bbox riêng cho glyph nhỏ.

| ID | Bank | Trang | Khoản mục nguồn | Cách đóng |
| --- | --- | ---: | --- | --- |
| A2025-GN-001 | ACB | 60 | Giao dịch bán và mua lại trái phiếu Chính phủ với KBNN | Map 1033 `Vay khác`; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-002 | HDB | 44 | Vay NHNN | Map 6070; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-003 | HDB | 44 | Vay chiết khấu các giấy tờ có giá | Map 1026; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-004 | HDB | 44 | Tiền gửi của Kho bạc Nhà nước | Map 1035; số so sánh `1` được xác thực từ crop render dù line detector bỏ sót. |
| A2025-GN-005 | VCB | 52 | Vay cầm cố GTCG | Map 1027; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-006 | CTG | 51 | Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước | Cộng có kiểm soát vào 1033; ô so sánh DASH pixel-bound = 0. |
| A2025-GN-007 | BID | 50 | Nhận vốn từ NHNN để tạm ứng cho Ban Xử lý nợ cho vay đặc biệt Ngân hàng TMCP Nam Đô | Cộng có kiểm soát vào 1033 `Vay khác`. |
| A2025-GN-008 | BID | 50 | Vay thực hiện dự án hiện đại hóa ngân hàng và Hệ thống Thanh toán của Ngân hàng bằng ngoại tệ | Cộng có kiểm soát vào 1033; ô hiện kỳ DASH pixel-bound = 0. |

Machine-readable result:
`docs/experiments/E-0128-annual-2025-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json`.

## OPEN — annual-2025 `Tài sản Có khác`

E-0127 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và tìm đúng một vùng
family tại mỗi bank. 134 mapping và 66 phương trình đã đóng; 35 dòng dưới đây
giữ nguyên nguồn và `UNRESOLVED` vì chưa có schema chính xác, dòng gộp không có
phân bổ, hoặc ô DASH chưa có numeric bbox độc lập.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| A2025-OA-001 | ACB | 58 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| A2025-OA-002 | ACB | 58 | Phải thu Ngân sách Nhà nước | Không nói đây là thuế nộp thừa/được khấu trừ để map 974. |
| A2025-OA-003 | ACB | 59 | Tài sản thuế thu nhập doanh nghiệp hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-004 | ACB | 59 | Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-005 | ACB | 60 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-006 | MBB | 62 | Phải thu liên quan đến tài trợ thương mại | Chưa có leaf tương đương; ô hiện kỳ là DASH. |
| A2025-OA-007 | MBB | 62 | Các khoản phải thu miễn truy đòi theo bộ chứng từ | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-008 | MBB | 62 | Các khoản tạm ứng và đặt cọc hợp đồng | Một dòng gộp 975/973, không có phân bổ nguồn. |
| A2025-OA-009 | MBB | 62 | Dự phòng phí và dự phòng bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có leaf tương đương. |
| A2025-OA-010 | MBB | 62 | Lãi phải thu hoạt động tín dụng và phí phải thu | Dòng gộp lãi tín dụng và phí, không thu hẹp vào 983. |
| A2025-OA-011 | MBB | 63 | Lợi thế thương mại | Ô hiện kỳ là DASH chưa có numeric bbox độc lập. |
| A2025-OA-012 | MBB | 63 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-013 | VPB | 55 | Phải thu bán tài sản tài chính | Rộng hơn 976 `Phải thu từ bán chứng khoán`. |
| A2025-OA-014 | VPB | 55 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có leaf tương đương. |
| A2025-OA-015 | VPB | 55 | Nợ đủ tiêu chuẩn | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-016 | VPB | 56 | Tài sản có khác | Ô so sánh là DASH chưa có numeric bbox độc lập. |
| A2025-OA-017 | VPB | 56 | Lợi thế thương mại | Ô hiện kỳ là DASH chưa có numeric bbox độc lập. |
| A2025-OA-018 | VPB | 57 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-019 | HDB | 42 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| A2025-OA-020 | HDB | 43 | Phải thu từ thanh lý TSCĐ | Ô hiện kỳ là DASH và chưa có leaf chính xác. |
| A2025-OA-021 | HDB | 44 | Dự phòng rủi ro các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-022 | VCB | 50 | Phải thu từ ngân sách Nhà nước về hỗ trợ lãi suất | Là phải thu ngân sách, không phải phải thu NHNN 979. |
| A2025-OA-023 | VCB | 51 | Tài sản thuế thu nhập hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-024 | VCB | 51 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-025 | CTG | 50 | Các khoản tạm ứng và phải thu nội bộ | Một dòng gộp 975/970, không có phân bổ nguồn. |
| A2025-OA-026 | CTG | 50 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-027 | BID | 49 | Các khoản phải thu khác | Parent gộp phải thu nội bộ và bên ngoài, không phải leaf hẹp 981. |
| A2025-OA-028 | BID | 49 | Tài sản thuế thu nhập doanh nghiệp hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-029 | BID | 49 | Dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh số dư/biến động dự phòng tương ứng. |
| A2025-OA-030 | BID | 49 | Phải thu trong nghiệp vụ tài trợ thương mại | Chưa có leaf tương đương. |
| A2025-OA-031 | VIB | 44 | Phải thu từ Ngân sách Nhà nước | Không đủ nghĩa để map vào 974 hoặc 979. |
| A2025-OA-032 | VIB | 44 | Phải thu từ hoạt động tài trợ thương mại | Chưa có leaf tương đương. |
| A2025-OA-033 | VIB | 44 | Phải thu hoa hồng bảo hiểm | Không xác định đối tác là công ty bảo hiểm con như 978 yêu cầu. |
| A2025-OA-034 | VIB | 44 | Tài sản thuế TNDN hoãn lại | Family 966–1023 chưa có leaf tương đương. |
| A2025-OA-035 | VIB | 44 | Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác | Ô hiện kỳ là DASH và chưa có nhánh dự phòng chính xác. |

Machine-readable result:
`docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json`.

## CLOSED HISTORY — annual-2025 `Chứng khoán đầu tư`

E-0121 quét toàn bộ tám BCTC hợp nhất kiểm toán năm 2025 và xác minh family tại
ACB p52–53, MBB p54–56, VPB p50–52, HDB p39–40, VCB p42–43, CTG p45–46,
BID p44–45 và VIB p40–41. Kết quả đã đóng 112 mapping, 224 ô giá trị và 72
phương trình. Hai hàng nguồn gộp dưới đây đã được chủ dự án adjudicate và
`VERIFIED_BY_CODEX` mà không tách giả giá trị in.

### E-0121-AIS-001 — MBB — government/government-guaranteed combined row

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 54.
- Source label: `Trái phiếu Chính phủ và trái phiếu Chính phủ bảo lãnh`.
- Nearest schema leaves: 807 và 5740.
- Structure/accounting: nằm đúng trong nhánh AFS duy nhất; giá trị nguồn tham gia
  đầy đủ các phương trình tổng đã đóng.
- Resolution: giữ nguyên số in gộp và map một lần vào 807 theo quyết định của
  chủ dự án; không đồng thời ghi 5740 nên không phát sinh double count.
- Status: `CLOSED — VERIFIED_BY_CODEX_AS_ONE_PRINTED_ROW_TO_807`.

### E-0121-AIS-002 — HDB — central-bank bill/government-security combined row

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 39.
- Source label: `Tín phiếu NHNN + Chứng khoán Chính phủ`.
- Nearest schema leaf: 831 `Chứng khoán nợ do Chính phủ phát hành`.
- Structure/accounting: nằm đúng trong nhánh HTM duy nhất; số nguồn và tổng family
  đã được pixel/PaddleOCR6/phương trình xác minh.
- Resolution: cộng có kiểm soát đúng hai hàng nguồn theo từng kỳ rồi map một lần
  vào 831: `0 + 3.225.821 = 3.225.821` và
  `13.250.000 + 3.386.590 = 16.636.590`.
- Status: `CLOSED — VERIFIED_CONTROLLED_TWO_ROW_AGGREGATION_TO_831`.

E-0122 `Các khoản đầu tư dài hạn khác` quét lại toàn bộ tám BCTC hợp nhất kiểm
toán annual-2025 và tìm đúng một vùng tại ACB p54, MBB p57, VPB p52, HDB p41,
VCB p44–45, CTG p47, BID p45 và VIB p41. 28 mapping, 56 ô giá trị và 11
phương trình đã được pixel/PaddleOCR6/schema/accounting replay xác minh; không
phát sinh dòng `OPEN` mới. Dấu `-` của CTG được map thành dự phòng 0 sau khi
bind ảnh; dấu `-` so sánh CAEX tại VPB chỉ dùng để đóng subtotal 5960 và không
được biến thành một khoản mục schema riêng. Vì không có issue mới, tổng ledger
và open queue ở đầu file không thay đổi.

E-0123 `Tăng, giảm tài sản cố định hữu hình` quét lại toàn bộ tám BCTC hợp nhất
kiểm toán annual-2025 và tìm đúng một vùng tại ACB p55, MBB p58, VPB p53, HDB
p41, VCB p48, CTG p48, BID p47 và VIB p42. 105 mapping và 32 phương trình
roll-forward/carrying-value đã được pixel, PP-OCRv6, schema và accounting replay
xác minh; không phát sinh dòng `OPEN` mới. CTG/BID/VIB dùng cùng một biến thể
hình học xoay, không có routing theo bank/page. VietOCR proposal VIB `164.02`
được giữ nguyên làm semantic evidence không đủ thẩm quyền số; numeric challenger
đọc `164.021` và phương trình nguồn xác nhận giá trị đó. Vì không có issue mới,
tổng ledger và open queue ở đầu file không thay đổi.

E-0125 `Tăng, giảm tài sản cố định vô hình` quét lại toàn bộ tám BCTC hợp nhất
kiểm toán annual-2025 và tìm đúng một vùng tại ACB p56, MBB p60, VPB p54, HDB
p42, VCB p49, CTG p49, BID p48 và VIB p43. 107 mapping và 32 phương trình
roll-forward/carrying-value đã được pixel, trục số PP-OCRv6 nguồn, schema và
accounting replay xác minh; không phát sinh dòng `OPEN` mới. Ba disclosure có
số nằm cùng câu được xử lý bằng một rule inline chung. VietOCR CTG đọc sai
`(65.998)`; pixel, PP-OCRv6 và phương trình đều khóa `(85.998)`. Kết quả
Q2/2026 và VPB Q1/2026 cũ vẫn byte-exact; tổng ledger và open queue không đổi.

E-0126 `Tăng, giảm bất động sản đầu tư` quét lại toàn bộ tám BCTC hợp nhất
kiểm toán annual-2025 và tìm đúng hai vùng duy nhất tại ACB p57 và MBB p61.
18 mapping cùng 27 phương trình được pixel, trục số PP-OCRv6 nguồn, family-local
schema và accounting replay xác minh; không phát sinh dòng `OPEN`. ACB có hai
bảng anh em `cho thuê`/`nắm giữ chờ tăng giá`: năm tổng family được cộng đúng
một lần từ các component đã xác minh, còn DASH được bind bằng hình học hàng–cột
trước khi chuẩn hóa 0. VPB/HDB/VCB/CTG/BID/VIB là bounded absence giữa family
TSCĐ vô hình và Tài sản Có khác trong đúng filing annual-2025. E-0072 hiện hành
vẫn byte-exact; tổng ledger và open queue không đổi.

E-0107 `Tiền, kim loại quý và đá quý` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p45,
MBB p46, VPB p41, HDB p33, VCB p35, CTG p39, BID p39 và VIB p35. 35 mapping
và tám phương trình tổng đã `VERIFIED_BY_CODEX`. VietOCR đọc số HDB
`1.194.005`, nhưng pixel cùng trục số nguồn xác nhận `1.194.085` và phương
trình đóng đúng; dấu gạch CTG bị provider bỏ sót được bind từ đúng ô ảnh rồi
chuẩn hóa 0. Hai bất đồng là đối chứng OCR đã đóng, không phải khoảng trống
mapping.

E-0108 `Tiền gửi tại NHNN` trên tám BCTC hợp nhất kiểm toán năm 2025 không
bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại cả tám bank và map 28
dòng với mười phương trình đóng chính xác. Tiền gửi tại ngân hàng trung ương
Lào/Campuchia được gom có kiểm soát vào 574 tại MBB/VCB/BID. Graph đã sửa lỗi
subtree tổng quát tại BID: các nhánh VND/ngoại tệ của từng jurisdiction phải
kết thúc trước khi tìm tổng family `123.629.833`. VietOCR HDB `B.416.558` được
pixel và trục số nguồn xác nhận là `8.416.558`; đây là lỗi OCR đã đóng.

E-0109 `Tiền, vàng gửi tại và cho vay/vay các TCTD khác` trên tám BCTC hợp
nhất kiểm toán năm 2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một
vùng tại ACB p46, MBB p48, VPB p42, HDB p34, VCB p36, CTG p40, BID p39 và VIB
p36; 86 mapping và 33 phương trình đóng chính xác. Các ô `DASH` của ACB được
bind từ pixel rồi chuẩn hóa 0. VietOCR HDB `27.921.364` được ảnh gốc, trục số
nguồn và phép cộng bác bỏ thành `27.921.384`. Dự phòng tổng tại MBB/VCB/BID
được map vào 5718. Đây đều là đối chứng đã đóng, không phải dòng OPEN.

E-0110 `Chứng khoán kinh doanh` trên tám BCTC hợp nhất kiểm toán năm 2025
không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p47, MBB
p49, VPB p43, HDB p34, VCB p37, CTG p41 và BID p40; VIB được xác nhận không
có family trading trong đúng báo cáo đã bind và family chứng khoán đầu tư của
VIB không bị relabel. 58 mapping và 21 phương trình đóng chính xác. Dấu `-`
hiện kỳ của HDB được bind từ pixel rồi chuẩn hóa 0. Bốn view tình trạng niêm
yết tại ACB/MBB/HDB/CTG được giữ làm đối chứng không cộng trùng. Đây là family
đã đóng, không tạo candidate hoặc dòng OPEN mới.

E-0111 `Công cụ tài chính phái sinh và tài sản/công nợ tài chính khác` trên
tám BCTC hợp nhất kiểm toán năm 2025 không bổ sung dòng OPEN: whole-PDF graph
tìm đúng một vùng tại ACB p49, MBB p66, VPB p44, HDB p35, CTG p42, BID p41 và
VIB p37; VCB được xác nhận không có family chi tiết trong báo cáo đã bind. 100
mapping và 62 phương trình đóng chính xác. Header nhiều tầng của MBB được phục
hồi thành bốn lane bằng quan hệ hình học, không bằng rule theo bank. 24 dấu `-`
được bind từ giao điểm hàng–cột rồi chuẩn hóa 0. VietOCR đọc dòng kiểm tra MBB
`173.426`; pixel, trục số nguồn và phép trừ xác nhận `173.425`. Đây là lỗi OCR
đã đóng, không phải dòng OPEN.

E-0112 `Phân tích theo loại hình cho vay` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p50,
MBB p51, VPB p45, HDB p35, VCB p39, CTG p43, BID p41 và VIB p37; 44 hàng nguồn
được `VERIFIED_BY_CODEX`, tám tổng family đóng chính xác và ba dấu `-` được giữ
typed trước khi chuẩn hóa 0. Các biến thể được thêm ở mức family, không theo
bank: `Số cuối năm/Số đầu năm`, bảng tiền/% bốn lane, khoản phải thu cho thuê
tài chính, thư tín dụng trả chậm và các cách gọi margin/đối tượng nước ngoài.
VietOCR HDB đọc tổng so sánh `442.464.841`; pixel và phép cộng các hàng xác nhận
`442.484.841`. Đây là lỗi OCR đã đóng, không phải khoảng trống mapping.

E-0113 `Phân tích cho vay theo ngành nghề kinh doanh` trên tám BCTC hợp nhất
kiểm toán năm 2025 tìm đúng một vùng tại ACB p51, MBB p52, VPB p47, HDB p37,
VCB p40, BID p42 và VIB p38; CTG được xác nhận không có family trong đúng filing
đã bind. 102 dòng nguồn được `VERIFIED_BY_CODEX`, 22 trục tiền tệ đóng đúng và
45 lỗi dấu/ký tự/dấu thập phân của VietOCR được giữ thành bất đồng đã kiểm tra.

### E-0113-LI-001 — VCB — `Thương mại, dịch vụ`

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 40.
- Source label: `Thương mại, dịch vụ`.
- Visible values: `240.272.006 | 214.488.774`.
- Structure/accounting: nằm đúng trong graph ngành duy nhất và cả hai trục đều
  tham gia phương trình tổng đã đóng.
- Resolution: schema có leaf gộp 6073 `Thương mại, dịch vụ`; giữ nguyên một số
  nguồn và map một lần, không phân bổ sang các leaf thành phần.
- Status: `CLOSED — VERIFIED_BY_CODEX_TO_COMBINED_SCHEMA_LEAF_6073`.

### E-0113-LI-002 — CTG — family không có trong filing annual-2025 đã bind

- Scan scope: toàn bộ BCTC hợp nhất kiểm toán năm 2025, dùng fresh VietOCR
  Transformer và kiểm tra các cặp anchor gần đúng.
- Result: không có bảng phân tích cho vay theo ngành; các vùng gần giống thuộc
  family khác và không vượt owner/child/period/unit/total checks.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; không suy rộng sang filing
  CTG khác.

E-0114 `Phân tích chất lượng cho vay` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p50,
MBB p51, VPB p45, HDB p36, VCB p39, CTG p43, BID p42 và VIB p66. 40 dòng năm
nhóm nợ cùng ba dòng margin độc lập ACB/MBB/VPB được map; 16 phương trình tiền
và hai phương trình phần trăm đóng đúng. HDB giữ population thư tín dụng trả
chậm kế bên ngoài core; VIB chọn đúng cột `Cho vay khách hàng` trong bảng năm
cột và không biến ô trống thành 0. Hai vùng chất lượng chứng khoán của CTG là
đối chứng âm sai owner. 14 lỗi chữ/dấu của VietOCR được pixel giải quyết; không
có bất đồng số trong 86 ô tiền. Family annual-2025 này đã đóng hoàn toàn.

E-0115 `Phân tích dư nợ theo thời gian/thời hạn gốc` trên tám BCTC hợp nhất
kiểm toán năm 2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng
tại ACB p50, MBB p51, VPB p45, HDB p36, VCB p40, CTG p44, BID p42 và VIB
p38. Cả 24 hàng lõi `Nợ ngắn hạn`/`Nợ trung hạn`/`Nợ dài hạn` cùng hai hàng
margin độc lập của MBB/VPB đã được map; 52 ô tiền, 8 ô tỷ lệ VIB và 26 phương
trình khép đúng. HDB có dân số thư tín dụng trả chậm kế bên: dòng này được xác
minh nguồn, tham gia kiểm tra tổng lớn nhưng nằm ngoài lõi kỳ hạn và không phải
khoản mục chưa map. Chín bất đồng chữ/số VietOCR được giữ minh bạch và giải
quyết bằng pixel cộng với quan hệ kế toán. Family annual-2025 này đã đóng hoàn
toàn.

E-0116 `Phân tích cho vay theo loại hình tiền tệ` trên tám BCTC hợp nhất kiểm
toán năm 2025 không bổ sung dòng OPEN. Graph chung tìm đúng một vùng tại ACB
p51 và HDB p37; bốn hàng 757/758, tám ô tiền và tám phương trình đã được xác
minh. MBB, VPB, VCB, CTG, BID và VIB không có family này trong ranh giới note
`Cho vay khách hàng` của filing annual-2025. Các cặp VND/ngoại tệ trong bảng
lãi suất và bảng liên ngân hàng là đối chứng âm. Dân số thư tín dụng trả chậm
của HDB được xác minh source-only ngoài lõi. Hai lỗi số Transformer
`418.599.083`/`442.484.641` được pixel, PaddleOCR6 và phương trình bác bỏ để
dùng `418.599.063`/`442.484.841`.

E-0117 `Phân tích dư nợ cho vay theo khu vực địa lý` trên tám BCTC hợp nhất
kiểm toán năm 2025 không bổ sung dòng OPEN. Graph chung tìm đúng một vùng tại
ACB p77, MBB p91 và VIB p59–60; sáu khoản mục 5752/765, 12 ô tiền và sáu
phương trình đã được xác minh. Dấu `-` của ACB/VIB được bind từ pixel trước khi
chuẩn hóa thành 0. VPB p81, HDB p60 và BID p63 là đối chứng địa lý có population
dư nợ rộng hơn `Cho vay khách hàng`, nên không bị thu hẹp ngầm; VCB/CTG không
có vùng đúng family. Kết quả là ba vùng unique và năm bounded-report absences,
không còn khoản mục geography annual-2025 chờ map.

E-0118 `Phân tích theo loại hình doanh nghiệp/đối tượng khách hàng` trên tám
BCTC hợp nhất kiểm toán năm 2025 tìm đúng một vùng tại MBB p52, VPB p46, HDB
p36, VCB p40, BID p42 và VIB p39; ACB/CTG không có complete region trong exact
fresh-VietOCR scan. 57 khoản mục, 114 ô tiền, 86 ô tỷ lệ và sáu tổng nguồn đã
được kiểm tra độc lập. Hai dấu `-` của MBB được bind từ pixel rồi mới chuẩn hóa
thành 0. JSON nhiều tầng từ ảnh toàn trang của Gemma chỉ là challenger cấu trúc;
matcher vẫn quyết định bằng owner/con/trật tự/hình học/trục kỳ/đơn vị và phép
cộng. Hàng gộp VCB được giữ nguyên và map một lần vào leaf 6074.

### E-0118-LE-001 — VCB — `Hợp tác xã và công ty tư nhân`

- Report: BCTC hợp nhất kiểm toán năm 2025; physical page 40.
- Source label: `Hợp tác xã và công ty tư nhân`.
- Visible values: `937.036 | 1.371.552`.
- Structure/accounting: nằm trong graph enterprise/customer-type duy nhất; cả
  hai trục tham gia tổng `Cho vay khách hàng` đã đóng chính xác.
- Resolution: schema có leaf gộp 6074 `Hợp tác xã và công ty tư nhân`; không
  chia giá trị nguồn sang 776/774 và không ghi trùng.
- Status: `CLOSED — VERIFIED_BY_CODEX_TO_COMBINED_SCHEMA_LEAF_6074`.

E-0119 `Dự phòng rủi ro cho vay khách hàng` trên tám BCTC hợp nhất kiểm toán
năm 2025 không bổ sung dòng OPEN. Whole-PDF graph tìm đúng một vùng tại ACB
p51, MBB p53, VPB p48, HDB p38, VCB p41, CTG p44, BID p43 và VIB p39. 18
lane cha, 79 dòng movement và 18 phương trình roll-forward đã được xác minh;
chín dấu `-` được bind từ pixel trước khi chuẩn hóa thành 0. MBB `2.476` của
VietOCR bị pixel và PaddleOCR6 bác bỏ để dùng `2.478`. Cột tổng và các lane
phụ chỉ là đối chứng; không còn khoản mục annual-2025 của family này chờ map.

E-0079 `Thu nhập lãi và các khoản thu nhập tương tự` không bổ sung dòng OPEN:
cả tám vùng duy nhất đã map hết các dòng nguồn vào 1143–1150. Hai lỗi mất chữ
số đầu của VietOCR tại VIB được trục số nguồn/PaddleOCR và pixel bác bỏ, nên là
đối chứng OCR đã đóng chứ không phải khoảng trống mapping.

E-0080 đóng GN-001–GN-004 và IVP-001–IVP-004/IVP-008 theo quyết định của chủ
dự án. Ba cách gọi khoản vay ngân hàng trung ương dùng schema mới 6070; tiền
gửi có kỳ hạn KBNN dùng 6071; tiền gửi Bộ Tài chính được chuyển từ 1039 sang
6072. ACB đúng 5 năm dùng biên kỳ hạn bao gồm 5 năm, MBB dùng trực tiếp hai
leaf rộng 6010/6009, và trái phiếu tăng vốn BIDV dùng 1117. Tại MBB, 6010
`Dưới 5 năm` và 1112 `Trên 5 năm` là hai hàng trái phiếu tách biệt; 6009 nhận
nguyên dòng chứng chỉ tiền gửi `Trên 12 tháng`. Chỉ ba trục kỳ hạn toàn family
của VPB còn OPEN.

E-0081 `Chi phí lãi và các khoản tương tự chi phí lãi` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một vùng tại cả tám bank và map đủ owner/tổng
1151 cùng bốn dòng con 1152/1153/1154/1156. ReportNormId 1155 được ghi nhận
không xuất hiện trong đúng tám vùng family đã bind. Lỗi VietOCR MBB
`(3:975.549)` được trục số nguồn và pixel bác bỏ thành `(3.975.549)`; đây là
đối chứng OCR đã đóng, không phải khoảng trống mapping.

E-0082 `Thu nhập/chi phí/lãi thuần từ hoạt động dịch vụ` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại MBB/VPB/VIB, map 43 dòng
vào 1157–1174, 5986–5989 và 6021–6025, đồng thời đóng 18 phương trình. Hai
dấu gạch ở `Chi về dịch vụ tư vấn` của MBB được pixel-bind và chuẩn hóa 0.
ACB/HDB/CTG/BID chỉ có tổng trên KQKD; VCB có thêm đối chứng báo cáo bộ phận;
không vùng nào có các hàng con của note nên năm báo cáo được ghi bounded
non-observation, không tạo candidate hoặc dòng OPEN giả.

E-0083 `Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối` không bổ sung
dòng OPEN: whole-PDF graph tìm đúng một note chi tiết tại MBB p47, VPB p63 và
VIB p46, map 23 dòng vào 1175–1185 cùng 6026–6027 và đóng 18 phương trình.
MBB dùng biến thể gộp ngoại tệ giao ngay + vàng với tổng cha ở cuối; VPB tách
vàng riêng; VIB không có dòng vàng; VPB/VIB dùng tổng cha ở đầu. ACB/HDB/VCB/
CTG/BID chỉ có dòng tổng KQKD hoặc đối chứng chính sách/rủi ro/tỷ giá, không có
các hàng con của note; năm báo cáo được ghi bounded non-observation, không tạo
candidate hay dòng OPEN giả. VPB giữ đúng kỳ Q1/2026.

E-0084 `Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/VCB/CTG/
BID, map 28 dòng vào 1188–1191 và đóng 14 phương trình hai kỳ. Dấu `-` kỳ so
sánh của HDB được pixel-bind và chuẩn hóa 0. PDF HDB thực sự in nhãn dự phòng
`chứng khoán đầu tư` bên trong owner chứng khoán kinh doanh; nhãn nguồn được
giữ nguyên, còn containment, vị trí hàng và hai phương trình xác nhận vai trò
1191 nên đây là caveat đã đóng, không phải sửa OCR hay dòng OPEN. VIB chỉ có
note mua bán chứng khoán đầu tư p46; vùng này là đối chứng family khác và không
bị relabel. VPB giữ đúng kỳ Q1/2026.

E-0085 `Lãi/lỗ thuần từ mua bán chứng khoán đầu tư` không bổ sung dòng OPEN:
whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/CTG/BID/VIB,
map 28 dòng vào 1193–1196 và 6028, đồng thời đóng 14 phương trình hai kỳ. MBB
có thêm nhánh dự phòng giảm giá góp vốn, đầu tư dài hạn; VIB không có nhánh dự
phòng. Ba dấu gạch ACB và một dấu gạch MBB được pixel-bind rồi chuẩn hóa 0. VCB
chỉ có số tổng báo cáo bộ phận, không có các hàng con của note nên là bounded
non-observation chứ không tạo candidate hoặc dòng OPEN. VPB giữ đúng kỳ Q1/2026.

E-0086 `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư` không bổ sung
dòng OPEN: whole-PDF graph chỉ tìm đúng một dòng tổng hợp có hai giá trị tại
MBB p47. Hai phương trình với net chứng khoán kinh doanh và net chứng khoán đầu
tư đóng đúng; bảy PDF còn lại không in dòng tổng hợp tương đương trong phạm vi
nguồn đã bind.

E-0087 `Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/VCB/CTG/
BID, map 27 dòng vào 1198–1204 và đóng 16 phương trình. Năm dấu gạch được bind
nguồn/pixel và chuẩn hóa 0; hai proposal VietOCR `1` của VPB bị native source
`-` bác bỏ. VIB chỉ có dòng tổng KQKD, không có note chi tiết nên là bounded
non-observation, không tạo candidate. VPB giữ đúng kỳ Q1/2026.

E-0088 `Chi phí quản lý chung (Chi phí hoạt động)` quét đủ 453 trang và tìm
đúng một note tại cả tám PDF. 99 dòng schema/198 ô số cùng 30 phương trình đã
`VERIFIED_BY_CODEX`; một lỗi mất chữ số của VietOCR tại VCB bị pixel và trục số
nguồn bác bỏ. OE-001–OE-004 vẫn OPEN vì là bốn ý nghĩa chi phí riêng chưa có
leaf schema tương đương; chúng vẫn được giữ trong parent/tổng nguồn và không
cản các mapping chắc chắn khác. VPB giữ đúng kỳ Q1/2026.

E-0089 `Chi phí dự phòng rủi ro tín dụng` quét đủ 453 trang và tìm đúng một
note chi tiết tại MBB p49, VPB p66 và VIB p47. 15 mapping/30 ô số và 8 phương
trình đã `VERIFIED_BY_CODEX`; hai dấu gạch không có OCR line được pixel-bind,
hai dấu gạch VPB bị VietOCR đọc thành `1` được native source bác bỏ. E-0100 đã
đóng CRPE-001/CRPE-002 vào 1228 `Dự phòng khác` theo quyết định chủ dự án và
tái kiểm tra tổng nguồn. ACB/HDB/VCB/CTG/BID được ghi nhận bounded absence
cho đúng note chi tiết trong các PDF đã bind, không phải vắng mặt số tổng KQKD.

E-0090 `Thu nhập, chi phí và lãi thuần từ hoạt động khác` quét đủ 453 trang và
tìm đúng một note chi tiết tại MBB p47, VPB p64 và VIB p46. 23 mapping/46 ô số
và 14 phương trình đã `VERIFIED_BY_CODEX`; MBB dùng biến thể net-only,
VPB/VIB dùng parent thu nhập + parent chi phí + các nhánh tùy chọn + lãi thuần.
Hai dòng thanh lý tài sản của VPB được cộng có kiểm soát theo từng kỳ. E-0100
đã cộng OACT-001 vào 1239 `Khác` đúng một lần và tái đóng parent thu nhập.
ACB/HDB/VCB/CTG/BID là bounded detailed-note absence; tổng KQKD, segment và
diễn giải không bị relabel thành note chi tiết. VPB giữ đúng kỳ Q1/2026.

E-0091 `Chi phí thuế thu nhập doanh nghiệp` quét đủ 453 trang và tìm đúng một
bảng đối chiếu chi tiết tại MBB p50, VPB p59 và VIB p48. 28 mapping/56 ô số và
20 phương trình đã `VERIFIED_BY_CODEX`; toàn bộ schema 5723–5737 được quan sát
và xác minh qua các biến thể. Hai dấu `-` của VPB chỉ được chuẩn hóa thành 0 sau
khi trục số nguồn xác nhận. TAX-001 còn OPEN vì VIB chỉ ghi `Điều chỉnh khác`,
kỳ hiện tại để trống và kỳ so sánh là `163`; nhãn này không đủ để ép vào leaf
5733 về điều chỉnh thuế của các năm trước. ACB/HDB/VCB/CTG/BID là bounded
detailed-note absence; tổng KQKD/nghĩa vụ thuế/thuế hoãn lại không bị relabel.

E-0092 `Tiền và các khoản tương đương tiền` quét đủ 453 trang và tìm đúng một
vùng chi tiết tại ACB p8, MBB p50, VPB p66, VCB p40, CTG p47 và VIB p45. 31
mapping/60 ô số và 12 phương trình đã `VERIFIED_BY_CODEX`, phủ toàn bộ family
1248–1254. Hai ô chứng khoán không in số được giữ trống thay vì đổi thành 0.
Không còn dòng nguồn chưa map trong sáu vùng. HDB/BID là bounded detailed-note
absence; số dư đầu/cuối kỳ và chính sách gần giống không bị relabel.

E-0093 `Mua mới và thanh lý các công ty con` quét đủ 453 trang và không tìm
thấy bảng nào có đủ ba dòng 1256–1258. Cả tám PDF là bounded detailed-note
absence, không phải khẳng định không có lịch sử giao dịch. HDB có HDS trở thành
công ty con nhưng đang áp dụng phương pháp tạm thời; CTG có caption dòng tiền
mua/bán công ty con. Các đối chứng này thiếu tổng giá trị, tiền thanh toán và
tiền thực có trong công ty con nên không phát sinh mapping hay dòng OPEN.

E-0094 `Thu nhập nhân viên của ngân hàng` quét đủ 453 trang và tìm đúng một
vùng chi tiết tại ACB p26, VPB p66 và VIB p49. 13 mapping/26 ô số và 14
phương trình tổng hoặc tỷ lệ đã `VERIFIED_BY_CODEX`. VPB giữ đúng kỳ Q1/2026;
VIB dùng kỳ sáu tháng. E-0100 chia hai số bình quân ACB cho đúng sáu tháng,
lưu phân số chính xác và map vào 1267/1268. MBB/HDB/VCB/CTG/BID không có bảng thu nhập nhân
viên chi tiết trong các PDF đã bind.

E-0095 `Tình hình thực hiện nghĩa vụ với ngân sách nhà nước` quét đủ 453
trang và tìm đúng một vùng tại ACB p22, MBB p49, VPB p58, HDB p32, CTG p43,
BID p26 và VIB p47. 33 mapping/147 ô số và 37 phương trình đã
`VERIFIED_BY_CODEX`. HDB dùng thêm trục tăng do hợp nhất; CTG tách phải nộp,
phải thu và số thuần cuối kỳ. 13 dấu gạch chỉ được chuẩn hóa thành 0 sau khi
xem pixel. E-0100 đưa `Tiền thuê đất` vào 1279 `Các khoản phải nộp khác`; năm
dấu gạch nhìn thấy đều bằng 0 nên mapping gộp không làm đổi tổng. VCB là bounded detailed-note absence; VPB giữ đúng
kỳ Q1/2026.

E-0096 `Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ` quét đủ
453 trang và tìm đúng một vùng tại VPB p67, VCB p47 và VIB p49. 15 mapping/30
ô số và sáu phương trình tổng đã `VERIFIED_BY_CODEX`. VIB dùng parent `Của
khách hàng` trong note chung nên nhánh `Của các TCTD khác` và tài sản chính
ngân hàng đưa đi thế chấp không bị nhập nhầm. E-0100 đã gộp CC-001–CC-004 vào
1288 `Khác` đúng một lần theo bank; hai tổng VCB/VIB tiếp tục đóng chính xác. ACB/MBB/HDB/CTG/
BID là bounded detailed-note absence; VPB giữ đúng kỳ Q1/2026.

E-0097 `Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu`
quét đủ 453 trang và tìm đúng một vùng tại VPB p67 và VIB p49. Năm mapping/10
ô số và sáu quan hệ thành phần đã `VERIFIED_BY_CODEX`; ACB/MBB/HDB/VCB/CTG/
BID là bounded detailed-note absence. BPA-001 giữ nguyên parent gộp của VPB vì
tổng nguồn in cộng cả parent lẫn các con “Trong đó”, nên hai phép tái hiện tổng
chỉ là source-presentation reconciliation chứ không phải accounting identity.
BPA-002/BPA-003 giữ hai hàng GTCG chung của VIB thay vì ép vào chứng khoán kinh
doanh/đầu tư khi PDF không in phân rã. VPB giữ đúng kỳ Q1/2026.

E-0098 `Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra` quét đủ 453 trang và tìm
đúng một note chi tiết tại ACB p26, MBB p51, VPB p68, CTG p48 và VIB p50.
47 mapping/92 ô số và 34 phương trình đã `VERIFIED_BY_CODEX`. VIB map cột
giá trị thuần sau ký quỹ; cột gộp và ký quỹ được giữ làm accounting controls.
CL-001–CL-005 và CL-007–CL-014 còn OPEN vì là các leaf L/C, ký quỹ, bảo lãnh
chi tiết, swap lãi suất hoặc `Trong đó` chưa có schema tương đương. HDB/VCB/BID
chỉ có bảng B02a và là bounded detailed-note absence; VPB giữ đúng kỳ Q1/2026.

E-0099 `Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý` quét đủ 453
trang và tìm đúng một bảng tại VPB p86, VCB p44–45 và CTG p51. 64 mapping/55
ô số và 12 phương trình đã `VERIFIED_BY_CODEX`; một dấu gạch CTG được
pixel-bind rồi chuẩn hóa 0. ACB/MBB/HDB/BID/VIB là bounded detailed-table
absence; các bảng rủi ro tiền tệ/lãi suất/thanh khoản là đối chứng âm. FI-001–
FI-003 giữ OPEN vì nguồn in `(*)` và ghi rõ giá trị hợp lý không xác định được;
không đổi `(*)` thành 0 hay sao chép giá trị ghi sổ. VPB giữ đúng kỳ Q1/2026.

E-0101 `Rủi ro tiền tệ` là base whole-PDF scan: sáu vùng duy nhất tại MBB p58,
VPB p80, HDB p38–39, VCB p50–51, CTG p60, VIB p65–66; ACB/BID là bounded
absence. E-0105 đóng CRISK-001/003–006/008/010–011 bằng quyết định làm tròn
±1, dấu gạch ngoại bảng bằng 0 và phạm vi bảng VCB→1418. Chỉ CRISK-002/007/009
còn OPEN vì schema chưa có trục vàng; không gộp vàng vào `Tiền tệ khác`.

E-0102 `Rủi ro lãi suất` là base whole-PDF scan: sáu vùng duy nhất tại MBB p57,
VPB p78, HDB p40–41, VCB p48–49, CTG p55, VIB p62–63; ACB/BID là bounded
absence. E-0105 đóng toàn bộ IRISK-001–IRISK-026. Dấu gạch được pixel-bind
thành 0; HDB được sửa vai trò dòng theo tọa độ đầy đủ; Gemma 4 đọc độc lập
bảng xoay VIB và 36 phương trình bác các chữ số rơi của challenger cũ. Family
hiện không còn dòng OPEN; VietOCR/Gemma vẫn không được dùng đơn lẻ làm numeric
truth. VPB giữ đúng kỳ Q1/2026.

E-0103 `Rủi ro thanh khoản` là base whole-PDF scan: sáu vùng duy nhất tại MBB
p60, VPB p82, HDB p43, VCB p53, CTG p58, VIB p68–69; ACB/BID là bounded
absence. E-0105 đóng LRISK-001/006–019: dấu gạch tổng nợ quá hạn bằng 0 và
Gemma 4 + full-table pixels đọc đủ VIB, khép 16 phương trình. Chỉ LRISK-002–005
còn OPEN vì bốn residual VPB lần lượt 6.000/275.500/6.001/275.499 là trọng yếu,
không được coi là làm tròn. VPB giữ đúng kỳ Q1/2026.

E-0104 `Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo` quét đủ 453 trang
và tìm đúng một vùng tại MBB p61, VPB p90, CTG p61, BID p35 và VIB p71;
ACB/HDB/VCB là bounded detailed-table absence. Graph chung dùng owner tỷ giá,
hai trục kỳ, đơn vị VND/đồng hoặc policy quy đổi VND cấp tài liệu và tối thiểu
hai hàng mã tiền tệ thẳng hàng; không dùng bank/page làm rule. Pixel, trục số
Paddle/native và live schema xác minh 46 mapping/92 ô, đồng thời giữ đủ 122 ô
nguồn. FXRATE-001–FXRATE-015 là 15 dòng tiền/vàng ngoài schema 5935–5945;
chúng đã được xác minh nguồn nhưng vẫn `OPEN`, không bị bỏ hoặc ép vào leaf
khác. VPB giữ đúng kỳ Q1/2026; BID dùng policy VND nhìn thấy tại p13.

## Open review queue (always first)

| ID | Family | Bank | Trang | Khoản mục nguồn | Lý do còn mở |
| --- | --- | --- | ---: | --- | --- |
| FXRATE-001 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | CNY | Không có leaf CNY dưới schema 5935–5945. |
| FXRATE-002 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-003 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | NZD | Không có leaf NZD dưới schema 5935–5945. |
| FXRATE-004 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | Vàng (XAU) | Không có leaf vàng/XAU dưới schema 5935–5945. |
| FXRATE-005 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | NZD | Không có leaf NZD dưới schema 5935–5945. |
| FXRATE-006 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | NOK | Không có leaf NOK dưới schema 5935–5945. |
| FXRATE-007 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-008 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | HKD | Không có leaf HKD dưới schema 5935–5945. |
| FXRATE-009 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | CNY | Không có leaf CNY dưới schema 5935–5945. |
| FXRATE-010 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | KRW | Không có leaf KRW dưới schema 5935–5945. |
| FXRATE-011 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | LAK | Không có leaf LAK dưới schema 5935–5945. |
| FXRATE-012 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-013 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | HKD | Không có leaf HKD dưới schema 5935–5945. |
| FXRATE-014 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | NOK | Không có leaf NOK dưới schema 5935–5945. |
| FXRATE-015 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | XAU | Không có leaf vàng/XAU dưới schema 5935–5945. |
| LRISK-001 | Rủi ro thanh khoản | MBB | 60 | Quá hạn — tổng tài sản/tổng nợ/chênh lệch ròng | `CLOSED_E0105`: tổng nợ in dấu `-` được chuẩn hóa 0; `28.949.005 - 0 = 28.949.005`. |
| LRISK-002 | Rủi ro thanh khoản | VPB | 82 | 1–3 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `+6.000` so với chênh lệch in. |
| LRISK-003 | Rủi ro thanh khoản | VPB | 82 | 1–5 năm — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `-275.500` so với chênh lệch in. |
| LRISK-004 | Rủi ro thanh khoản | VPB | 82 | 3–12 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `-6.001` so với chênh lệch in. |
| LRISK-005 | Rủi ro thanh khoản | VPB | 82 | Đến 1 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `+275.499` so với chênh lệch in. |
| LRISK-006–LRISK-007 | Rủi ro thanh khoản | HDB | 43 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-008–LRISK-009 | Rủi ro thanh khoản | VCB | 53 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-010–LRISK-011 | Rủi ro thanh khoản | CTG | 58 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-012–LRISK-019 | Rủi ro thanh khoản | VIB | 68–69 | Tám trục, 48 ô kỳ hiện tại/so sánh | `CLOSED_E0105`: full-table pixels + Gemma 4 challenger khớp; 16 phương trình tài sản − nợ = chênh lệch khép đúng. |
| IRISK-001–IRISK-002 | Rủi ro lãi suất | MBB/VPB | 57/78 | Quá hạn MBB và tổng trạng thái VPB | `CLOSED_E0105`: dấu `-` = 0; hai phương trình khép đúng. |
| IRISK-003–IRISK-011 | Rủi ro lãi suất | HDB | 41 | Chín trục nội/ngoại/kết hợp | `CLOSED_E0105`: sửa vai trò dòng theo full-render geometry; 18 phương trình khép đúng. |
| IRISK-012–IRISK-015 | Rủi ro lãi suất | VCB | 49 | Bốn trạng thái kết hợp | `CLOSED_E0105`: ngoại bảng in dấu `-` = 0; kết hợp bằng nội bảng. |
| IRISK-016–IRISK-017 | Rủi ro lãi suất | CTG | 55 | Hai trục quá hạn | `CLOSED_E0105`: tổng nợ in dấu `-` = 0; hai phương trình khép đúng. |
| IRISK-018–IRISK-026 | Rủi ro lãi suất | VIB | 62–63 | Chín trục × năm vai trò × hai kỳ = 90 ô | `CLOSED_E0105`: 69 crop cũ + 10 crop bổ sung + 11 dash pixel được Gemma 4/pixel đọc lại; 36 phương trình khép đúng. |
| CRISK-001 | Rủi ro tiền tệ | VPB | 80 | EUR — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | `CLOSED_E0105`: giữ nguyên bốn số nguồn; residual đúng 1 được adjudicate là sai số trình bày/làm tròn, không sửa số. |
| CRISK-002 | Rủi ro tiền tệ | VPB | 80 | Vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Family 1352 chưa có nhánh currency-axis vàng; bốn ô vẫn khép nội bảng. |
| CRISK-003–CRISK-005 | Rủi ro tiền tệ | VPB | 80 | OTHER/TOTAL/USD | `CLOSED_E0105`: map trực tiếp trạng thái kết hợp nhìn thấy; residual TOTAL đúng 1 được giữ là sai số trình bày. |
| CRISK-006 | Rủi ro tiền tệ | HDB | 39 | Trạng thái nội, ngoại bảng — EUR | `CLOSED_E0105`: ngoại bảng in `-` = 0; `3.919 + 0 = 3.919`. |
| CRISK-007 | Rủi ro tiền tệ | HDB | 39 | Vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Schema chưa có nhánh currency-axis vàng. |
| CRISK-008 | Rủi ro tiền tệ | VCB | 51 | Tổng nợ phải trả — VND | `CLOSED_E0105`: tiêu đề/phạm vi bảng cho phép map giá trị vào 1418 theo quyết định chủ dự án. |
| CRISK-009 | Rủi ro tiền tệ | CTG | 60 | Vàng — tổng tài sản, trạng thái nội bảng/kết hợp | Nguồn để trống tổng nợ và ngoại bảng vàng; schema cũng chưa có nhánh vàng. |
| CRISK-010–CRISK-011 | Rủi ro tiền tệ | VIB | 65 | Trạng thái kết hợp EUR/USD kỳ hiện tại | `CLOSED_E0105`: ngoại bảng in `-` = 0; kết hợp bằng nội bảng trên cả hai trục. |
| FI-001 | Công cụ tài chính | VPB | 86 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Nguồn ghi không thể xác định giá trị hợp lý; ký hiệu không phải 0 và giá trị ghi sổ không thay thế được. |
| FI-002 | Công cụ tài chính | VCB | 45 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Không có giá trị số được công bố; giữ nguyên nhóm nguồn OPEN. |
| FI-003 | Công cụ tài chính | CTG | 51 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Không có giá trị số được công bố; giữ nguyên nhóm nguồn OPEN. |
| CL-001 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Thư tín dụng trả ngay | Parent 1295 chưa có leaf L/C trả ngay; số vẫn đóng đúng L/C thuần. |
| CL-002 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Thư tín dụng trả chậm | Parent 1295 chưa có leaf L/C trả chậm; số vẫn đóng đúng L/C thuần. |
| CL-003 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Trừ: tiền ký quỹ (L/C) | Đây là trục khấu trừ để ra L/C thuần, không phải leaf giá trị hiện có. |
| CL-004 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Bảo lãnh khác (dòng con) | Dòng con lặp lại tên parent `Bảo lãnh khác`; chưa có leaf riêng để không map hai lần vào 1300. |
| CL-005 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Trừ: tiền ký quỹ (bảo lãnh) | Trục khấu trừ đóng đúng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-007 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trừ: tiền ký quỹ (L/C) | Trục khấu trừ đóng đúng L/C thuần nhưng chưa có leaf schema. |
| CL-008 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết bảo lãnh khác | Dòng con nằm trong parent `Bảo lãnh khác`; chưa có leaf riêng để tránh double mapping. |
| CL-009 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trừ: tiền ký quỹ (bảo lãnh) | Trục khấu trừ đóng đúng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-010 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất tiền tệ chéo — nhận | Schema hoán đổi tiền tệ 1302/5743–5744 chưa có leaf swap lãi suất chéo nhận. |
| CL-011 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất tiền tệ chéo — trả | Schema chưa có leaf swap lãi suất chéo trả. |
| CL-012 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất một đồng tiền | Schema chưa có leaf swap lãi suất một đồng tiền. |
| CL-013 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết khác (dòng con) | Dòng con lặp tên parent 1304; giữ trong phương trình parent, không map hai lần. |
| CL-014 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang | Dòng `Trong đó` là non-additive và chưa có leaf riêng. |
| BPA-001 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VPB | 67 | Giấy tờ có giá đưa đi thế chấp, cầm cố | Parent gộp bằng hai con “Trong đó”, nhưng tổng nguồn lại cộng parent và hai con lần nữa; giữ source-only, không biến hierarchy double-count thành accounting identity. |
| BPA-002 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VIB | 49 | Giấy tờ có giá đưa đi thế chấp, cầm cố | Nguồn không tách chứng khoán kinh doanh/đầu tư nên không ép vào 1290/1291. |
| BPA-003 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VIB | 49 | Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu | Nguồn không tách loại chứng khoán; family 1289–1293 chưa có leaf mục đích sử dụng tương đương. |
| TAX-001 | Chi phí thuế thu nhập doanh nghiệp | VIB | 48 | Điều chỉnh khác | Nhãn rộng hơn leaf 5733; kỳ hiện tại để trống và không được coi là 0, kỳ so sánh `163` vẫn tham gia phương trình tổng thuế hiện hành đã xác minh. |
| OE-001 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi thuê tài sản | Chưa có leaf riêng dưới 1212 `Chi về tài sản`; dòng vẫn nằm trong parent nguồn đã xác minh. |
| OE-002 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi phí công nghệ thông tin | Chưa có leaf chi phí CNTT tương đương trong family 1205–1220. |
| OE-003 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi về thuế GTGT đầu vào không được khấu trừ | Chưa có leaf chi phí VAT đầu vào không khấu trừ tương đương. |
| OE-004 | Chi phí quản lý chung (Chi phí hoạt động) | CTG | 47 | Chi khác về TSCĐ | Chưa có leaf riêng dưới 1212; hai số nguồn vẫn đóng đúng phương trình `khấu hao + chi khác về TSCĐ = chi về tài sản`. |
| CAF-001 | Vốn và các quỹ | VPB | 60 | Quỹ đầu tư phát triển | Chưa có cột số dư vốn tương đương trong schema; giá trị vẫn nằm trong tổng vốn đã xác minh. |
| CAF-002 | Vốn và các quỹ | VPB | 60 | Cổ phiếu quỹ | Không đồng nhất với nhánh số lượng cổ phiếu 5953; dấu gạch không được tự dùng làm numeric authority. |
| CAF-003 | Vốn và các quỹ | HDB | 33 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; cột trống không bị đổi thành 0. |
| CAF-004 | Vốn và các quỹ | HDB | 33 | Quỹ đầu tư xây dựng cơ bản | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| CAF-005 | Vốn và các quỹ | VCB | 36 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong subtotal quỹ và tổng vốn đã xác minh. |
| CAF-006 | Vốn và các quỹ | CTG | 43 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; dòng trống không bị đổi thành 0. |
| CAF-007 | Vốn và các quỹ | CTG | 43 | Chênh lệch đánh giá lại tài sản | Chưa có cột số dư vốn tương đương trong schema. |
| CAF-008 | Vốn và các quỹ | CTG | 43 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| CAF-009 | Vốn và các quỹ | BID | 27–28 | Báo cáo tình hình thay đổi vốn chủ sở hữu | Cấu trúc bảng xoay đã unique; OCR số nguồn không đủ tin cậy nên chưa map, và VietOCR text không được dùng làm numeric truth. |
| CAF-010 | Vốn và các quỹ | VIB | 44–45 | Báo cáo tình hình thay đổi vốn chủ sở hữu | Cấu trúc bảng xoay đã unique; OCR số nguồn không đủ tin cậy nên chưa map, và VietOCR text không được dùng làm numeric truth. |
| OPL-001 | Các khoản phải trả và công nợ khác | ACB | 22 | Thu nhập chưa thực hiện | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-002 | Các khoản phải trả và công nợ khác | ACB | 22 | Quỹ phát triển khoa học và công nghệ | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-003 | Các khoản phải trả và công nợ khác | VPB | 57 | Các khoản khách hàng trả trước | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-004 | Các khoản phải trả và công nợ khác | VPB | 57 | Doanh thu chờ phân bổ | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-005 | Các khoản phải trả và công nợ khác | VPB | 57 | Dự phòng nghiệp vụ bảo hiểm | `CLOSED_E0132A`: map 1127 `Khác`, không ép sang 1125. |
| OPL-006 | Các khoản phải trả và công nợ khác | VPB | 57 | Các khoản treo chờ chuyển tiền | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-007 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả hoạt động thanh toán thẻ | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-008 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả nhà cung cấp | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-009 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả các khoản vay khách hàng của VPBankS | `CLOSED_E0132A`: map 1127 `Khác`; giữ nguyên nghĩa vụ công ty con. |
| OPL-010 | Các khoản phải trả và công nợ khác | VPB | 57 | Tiền giữ hộ và đợi thanh toán | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-011 | Các khoản phải trả và công nợ khác | CTG | 43 | Các khoản lãi, phí phải trả | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-012 | Các khoản phải trả và công nợ khác | VIB | 43 | Các khoản lãi, phí phải trả | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| OPL-013 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả cổ tức cho cổ đông | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả nội bộ. |
| OPL-014 | Các khoản phải trả và công nợ khác | VIB | 43 | Tiền giữ hộ và đợi thanh toán | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-015 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả thanh toán giữa các TCTD | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-016 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả chuyển tiền chờ thanh toán | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-017 | Các khoản phải trả và công nợ khác | VIB | 43 | Các khoản chờ thanh toán khác | `CLOSED_E0132A`: map 1127 `Khác`; non-additive với parent phải trả bên ngoài. |
| OPL-018 | Các khoản phải trả và công nợ khác | VIB | 43 | Doanh thu chờ phân bổ | `CLOSED_E0132A`: map 1127 `Khác`; giữ trong tổng family, không cộng lặp. |
| PM-001 | Dự phòng rủi ro cho vay khách hàng | VPB | 45 | Dự phòng chung, dự phòng cụ thể, dự phòng cho vay giao dịch ký quỹ và ứng trước | Đã map và kiểm tra đủ kỳ 01/01–31/03/2026 của PDF được cung cấp; chưa có PDF VPB Q2/2026 nên không được relabel kết quả Q1 thành Q2. |
| OA-001 | Tài sản Có khác | VPB | 51 | Phải thu bán tài sản tài chính | Nghĩa nguồn rộng hơn 976 `Phải thu từ bán chứng khoán`; không thu hẹp ngầm. |
| OA-002 | Tài sản Có khác | VPB | 51 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có khoản mục con tương đương trong family 966–1023. |
| OA-003 | Tài sản Có khác | VPB | 52 | Số dư đầu kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-004 | Tài sản Có khác | VPB | 52 | Trích lập dự phòng rủi ro trong kỳ | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-005 | Tài sản Có khác | VPB | 52 | Số dư cuối kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-006 | Tài sản Có khác | VPB | 52 | Dự phòng tài sản Có rủi ro tín dụng | Đây là phân rã số dư dự phòng, không phải population chất lượng 1018. |
| OA-007 | Tài sản Có khác | VPB | 52 | Dự phòng cụ thể | Chưa có khoản mục dự phòng `Tài sản Có khác`. |
| OA-008 | Tài sản Có khác | VPB | 52 | Dự phòng rủi ro phải thu khó đòi | Chưa có khoản mục con tương đương. |
| OA-009 | Tài sản Có khác | VIB | 39 | Phải thu từ Ngân sách Nhà nước | Không đồng nhất với 979 `Phải thu từ NHNN Việt Nam`. |
| OA-010 | Tài sản Có khác | VIB | 39 | Phải thu từ hoạt động tài trợ thương mại | Chưa có khoản mục con tương đương. |
| OA-011 | Tài sản Có khác | VIB | 39 | Phải thu hoa hồng bảo hiểm | Chưa chứng minh tương đương khoản phải thu từ công ty bảo hiểm con. |
| OA-012 | Tài sản Có khác | VIB | 39 | Tài sản thuế TNDN hoãn lại | Chưa có khoản mục con tương đương trong family 966–1023. |
| IVP-005 | Phát hành giấy tờ có giá | VPB | 56 | Dưới 12 tháng | Trục kỳ hạn áp dụng cho toàn family gồm chứng chỉ tiền gửi và trái phiếu, không riêng một instrument leaf. |
| IVP-006 | Phát hành giấy tờ có giá | VPB | 56 | Từ trên 12 tháng đến 5 năm | Trục kỳ hạn toàn family, không được gán riêng vào CD/kỳ phiếu/trái phiếu. |
| IVP-007 | Phát hành giấy tờ có giá | VPB | 56 | Từ trên 5 năm trở lên | Trục kỳ hạn toàn family, không được gán riêng vào CD/kỳ phiếu/trái phiếu. |

The shared family locator follows a strict minimal-anchor search.  It enumerates
every parent+child pair first, then every child+child pair, over both complete and
near branch regions in the entire PDF.  If one pair is unique it stops; if pairs
collide it tries every remaining pair before expanding to parent+two-child or
three-child combinations.  Large monetary rows only prioritize which pair is
tested first.  They do not grant mapping authority.  The selected pair locates a
region but never truncates it: the retained graph still contains every observed
row, axis, optional branch, total and accounting relation.  Sibling order is not
fixed, while the parent must precede its descendant region.  No bank, filename,
page or note identifier participates in this decision.

| IDs | Current disposition |
| --- | --- |
| LG-001–LG-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; MBB/VIB alone have the exact customer-loan geography family. Five broader total-loan tables and VCB's segment report stay negative controls, never narrowed or relabelled |
| IDL-001–IDL-002 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận HDB/VCB bắt đầu thuyết minh từ family 592 |
| CBD-001–CBD-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; hai dòng cộng thành 2.148.359 và map vào ReportNormId 574 `Tiền gửi khác` |
| LT-001–LT-002 | `RESOLVED_VERIFIED_BY_CODEX` |
| LI-001, LI-008, LI-009 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT` |
| LI-002–LI-007, LI-010–LI-011 | `RESOLVED_VERIFIED_BY_CODEX` |
| LE-001–LE-011 | `RESOLVED` by exact family replay, non-additive graph equivalence, or pixel replay |
| CD-001–CD-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VPB `64.165` và VIB `174` map vào schema 770 đã đổi tên để bao quát MTV hoặc trên MTV có vốn Nhà nước trên 50% |
| PM-001 | `OPEN_SOURCE_PERIOD_GAP`; không còn dòng nguồn chưa map trong PDF Q1 đã bind |
| SEC-001 | `RESOLVED_VERIFIED_BY_CODEX`; E-0067 đã xử lý AFS VIB, map trực tiếp 807/824 và chuyển riêng phép gộp TCTD sang IS-002 |
| CPM-001–CPM-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận các mốc bắt đầu thuyết minh loại trừ family 561 trong năm PDF |
| IS-001 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; BID p23 kế thừa tuyên bố `Triệu VND` nhìn thấy tại p13 của cùng PDF và toàn vùng AFS/HTM được replay-bound |
| IS-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VIB gộp đúng hai dòng TCTD theo từng kỳ vào ReportNormId 808, giữ nguyên hai thành phần và hai phương trình |
| DFI-001 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận VCB không có thuyết minh family 631 |
| IFA-001–IFA-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng biến động TSCĐ vô hình chi tiết trong PDF đã bind |
| IFA-006 | `RESOLVED_VERIFIED_BY_CODEX`; schema 6069 được thêm và map cho disclosure TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng tại VPB/VIB |
| IP-001–IP-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/VPB/HDB/VCB/CTG/BID/VIB không có bảng biến động bất động sản đầu tư chi tiết trong đúng PDF đã bind; statement, policy, cash-flow và expense mentions giữ làm đối chứng âm |
| OA-001–OA-012 | `OPEN_SCHEMA_OR_SEMANTIC_GAP`; 58 khoản mục chắc chắn vẫn đã map, 12 dòng này được giữ nguyên nguồn và không ép vào schema gần nhất |
| GN-001–GN-004 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; ba nhãn vay NHNN/Ngân hàng Trung ương map 6070, tiền gửi có kỳ hạn KBNN map 6071; BID `Tiền gửi Bộ Tài chính` được chuyển khỏi 1039 sang 6072 |
| EIR-001–EIR-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID chuyển từ tiền gửi khách hàng thẳng sang family nợ kế tiếp, không có note vốn nhận tài trợ/ủy thác trong PDF đã bind |
| EIR-006–EIR-007 | `RESOLVED_VERIFIED_BY_CODEX`; hai nguồn nhỏ chưa có leaf riêng — ODA của VPB và chương trình nhà ở qua NHNN của VIB — giữ nguyên nhãn nguồn và map vào leaf `Khác` 1099 |
| IVP-001–IVP-004, IVP-008 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; ACB đúng 5 năm map 1103/1111, MBB broad tenor map trực tiếp 6009/6010, BID trái phiếu tăng vốn map 1117 |
| IVP-005–IVP-007 | `OPEN_SOURCE_SCOPE_GAP`; ba kỳ hạn VPB áp dụng cho toàn family, chưa có phân bổ nhìn thấy theo từng công cụ |
| OPL-001–OPL-018 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; E-0132A map toàn bộ vào 1127 `Khác`, giữ nguyên 36 giá trị nguồn và không cộng lặp với parent/tổng |
| OE-001–OE-004 | `OPEN_SCHEMA_GAP`; 99 khoản mục chắc chắn vẫn đã map. Bốn dòng chi phí riêng được giữ trong parent/tổng và các phương trình nguồn, không ép vào leaf gần nghĩa |
| CRPE-001–CRPE-002 | `CLOSED_BY_PROJECT_OWNER_TO_1228`; E-0100 giữ nguyên bốn giá trị nguồn, map hai dòng vào `Dự phòng khác` và tái đóng đúng tổng VPB/VIB |
| CRPE-003–CRPE-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có note chi tiết 1221 trong PDF đã bind, dù có thể có dòng tổng KQKD hoặc diễn giải chính sách |
| OACT-001 | `CLOSED_BY_PROJECT_OWNER_TO_1239`; E-0100 cộng `41 / 9` vào dòng Khác hiện có đúng một lần và tái đóng parent thu nhập VPB |
| OACT-002–OACT-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có note hoạt động khác chi tiết trong PDF đã bind; tổng KQKD, segment và diễn giải là đối chứng âm |
| TAX-001 | `OPEN_SCHEMA_GAP_WITH_BLANK_CURRENT_AXIS`; 28 khoản mục chắc chắn vẫn đã map. Dòng VIB `Điều chỉnh khác` chỉ có số kỳ so sánh `163`; ô kỳ hiện tại trống không bị đổi thành 0 và nhãn không bị ép vào 5733 |
| TAX-002–TAX-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng đối chiếu chi phí thuế chi tiết trong PDF đã bind |
| CEQ-001–CEQ-002 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; HDB/BID không có bảng chi tiết tiền và tương đương tiền 1248–1254 trong PDF đã bind; số dư lưu chuyển tiền tệ và diễn giải chính sách là đối chứng âm |
| SAD-001–SAD-008 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; cả tám PDF không có bảng chi tiết 1255–1258. Giao dịch HDS của HDB và caption dòng tiền CTG được giữ làm đối chứng, không bị relabel |
| EI-001–EI-002 | `CLOSED_BY_PROJECT_OWNER_MONTHLY_DERIVATION`; E-0100 chia chính xác các số sáu tháng cho 6: lương `15 / 43÷3`, thu nhập `81÷2 / 247÷6`, rồi map 1267/1268 |
| SBO-001 | `CLOSED_BY_PROJECT_OWNER_TO_1279`; năm dấu gạch HDB được pixel-bind thành 0 và gộp vào `Các khoản phải nộp khác`, không làm đổi tổng |
| CC-001–CC-004 | `CLOSED_BY_PROJECT_OWNER_TO_1288`; E-0100 gộp một lần vào dòng Khác hiện có. VCB 1288 thành `688.039.608 / 687.893.688`; VIB thành `204.865.534 / 153.501.606`, và hai total đóng đúng |
| BPA-001–BPA-003 | `OPEN_SOURCE_HIERARCHY_OR_SCHEMA_GAP`; VPB parent gộp bị tổng nguồn cộng lặp với các con, còn hai hàng VIB không tách loại chứng khoán; không dòng nào bị ép vào hierarchy/leaf hẹp |
| CL-001–CL-005, CL-007–CL-014 | `OPEN_SCHEMA_OR_SOURCE_HIERARCHY_GAP`; 47 mapping chắc chắn và 34 phương trình vẫn đã xác minh; các leaf/trục khấu trừ/`Trong đó` chưa tương đương được giữ nguyên nguồn |
| CL-023–CL-025 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; HDB/VCB/BID có bảng B02a ngoài báo cáo chính nhưng không có note B05a chi tiết của family trong đúng PDF đã bind |
| FI-001–FI-003 | `OPEN_SOURCE_VALUE_UNAVAILABLE`; VPB/VCB/CTG in `(*)` thay cho phần lớn giá trị hợp lý. Ký hiệu này không được đổi thành 0 hoặc thay bằng giá trị ghi sổ |
| FI-007–FI-011 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/MBB/HDB/BID/VIB không có bảng chi tiết đồng thời trình bày giá trị ghi sổ và giá trị hợp lý trong đúng PDF đã bind |
| CRISK-001/003–006/008/010–011 | `CLOSED_BY_E0105_PROJECT_OWNER_ADJUDICATION`; dấu gạch ngoại bảng = 0, VCB VND→1418, hai residual đúng 1 giữ nguyên nguồn như sai số trình bày |
| CRISK-002/007/009 | `OPEN_NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH`; 11 ô vàng không bị gộp vào tiền tệ khác |
| CRISK-012–CRISK-013 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro tiền tệ chi tiết trong đúng PDF đã bind |
| IRISK-001–IRISK-026 | `CLOSED_BY_E0105_PIXEL_GEMMA4_AND_ACCOUNTING_REPLAY`; đủ 234 mapping/279 ô và 108 phương trình; không còn OPEN |
| IRISK-027–IRISK-028 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro lãi suất chi tiết trong đúng PDF đã bind |
| LRISK-001/006–019 | `CLOSED_BY_E0105_DASH_ZERO_PIXEL_GEMMA4_AND_ACCOUNTING_REPLAY`; MBB/HDB/VCB/CTG và toàn bộ VIB đã khép |
| LRISK-002–LRISK-005 | `OPEN_MATERIAL_SOURCE_PRESENTATION_RESIDUAL`; bốn trục VPB lệch 6.000/275.500/6.001/275.499, không coi là làm tròn |
| LRISK-020–LRISK-021 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro thanh khoản chi tiết trong đúng PDF đã bind |

## Financial instruments — carrying and fair value (`FINANCIAL_INSTRUMENTS`)

- **FI-001–FI-003 — OPEN:** VPB p86, VCB p45 và CTG p51 dùng `(*)` cho các
  ô giá trị hợp lý không xác định được. Ba nhóm được giữ nguyên nguồn; không
  suy diễn 0 và không sao chép số ghi sổ.
- **FI-007–FI-011 — confirmed bound-report absences:** ACB, MBB, HDB, BID và
  VIB không có bảng chi tiết mang đồng thời hai nhánh giá trị ghi sổ/giá trị
  hợp lý. Các bảng rủi ro là matched controls thuộc family kế tiếp.

## Currency risk (`CURRENCY_RISK`)

Current exact-replay results: E-0101 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique currency-risk regions and
  confirms two bounded absences. Flexible axis/row order and page continuation
  are admitted; interest, liquidity and fair-value tables remain controls.
- E-0105 raises the verified denominator to 120 mappings/136 value cells and
  51 exact equations. Visible dashes become zero; the two VPB residuals of one
  remain unchanged and are explicitly bounded as presentation rounding.
- **CRISK-002/007/009 — OPEN:** only the three gold axes remain because the
  live schema has no gold branch. No gold value is collapsed into `OTHER`.

## Interest-rate risk (`INTEREST_RATE_RISK`)

Current exact-replay results: E-0102 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique interest-rate-risk regions
  and confirms two bounded absences. Flexible repricing axes/order, split-line
  labels, optional internal/external states and adjacent-page continuation are
  admitted; currency, liquidity and fair-value tables remain controls.
- E-0105 closes every gap: 234 mappings/279 value cells and 108 exact
  equations across all six present banks. VIB p62–63 uses pixel-bound Gemma 4
  as an independent challenger and 36 equations; neither OCR reader alone is
  numeric authority. VPB remains Q1/2026.
- **No IRISK entry remains OPEN.**

## Liquidity risk (`LIQUIDITY_RISK`)

Current exact-replay results: E-0103 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique liquidity-risk regions and
  confirms two bounded absences. Combined/split overdue axes, flexible
  maturity buckets, source-row aggregation and continuation are admitted;
  currency, interest-rate and fair-value tables remain controls.
- E-0105 raises the verified denominator to 129 mappings/153 value cells and
  51 exact `assets - liabilities = net liquidity gap` equations. VIB p68–69
  is fully closed by full-table pixels, Gemma 4 challenge and 16 equations.
- **LRISK-002–LRISK-005 — OPEN:** only four material VPB residuals remain;
  they are not silently treated as rounding.

## End-period exchange rates (`EXCHANGE_RATE`)

Current exact-replay result:
`docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json`

- One bank-blind whole-PDF graph finds five unique exchange-rate regions at
  MBB p61, VPB p90, CTG p61, BID p35 and VIB p71 and confirms three bounded
  detailed-table absences. Flexible row order, punctuation/grouping variants,
  split period axes and document-level VND policy inheritance are admitted;
  currency-risk, interest-rate-risk, liquidity-risk and policy prose remain
  controls.
- 46 mappings/92 current-comparative value cells are independently verified.
  All 122 visible source cells remain present; VietOCR is text/geometry
  evidence only and the Paddle/native source axis plus pixels controls numbers.
- **FXRATE-001–FXRATE-015 — OPEN:** retain CNY/DKK/NZD/XAU at VPB,
  NZD/NOK/DKK/HKD/CNY/KRW/LAK at CTG and DKK/HKD/NOK/XAU at VIB. These are
  valid source rows with no live TM leaf under 5935–5945; none is discarded or
  forced into another currency.

## Project-owner catch-all and monthly-average closure (`E-0100`)

Exact-replay overlay:
`docs/experiments/E-0100-owner-adjudicated-catchall-average-closure-v1.json`

- Closes **10** prior OPEN source rows without rewriting E-0089/E-0090/E-0094/
  E-0095/E-0096: CRPE-001/002 → 1228, OACT-001 → 1239, EI-001/002 →
  derived 1267/1268, SBO-001 → 1279 and CC-001–004 → 1288.
- Catch-all rows are aggregated once with any existing same-ID row; 10
  accounting equations replay exactly. ACB's monthly values retain exact
  rational numerators/denominators rather than an untracked rounded float.

## Bank-owned pledged or discounted assets (`BANK_PLEDGED_OR_DISCOUNTED_ASSETS`)

Current exact-replay result:
`docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique bank-owned asset region at VPB p67 and
  VIB p49. ACB/MBB/HDB/VCB/CTG/BID have no detailed note in the supplied
  reports; customer collateral and borrowing-facility text remain controls.
- Five mappings, 10 value cells and six component relations are independently
  verified. Two additional VPB printed-total reproductions are explicitly not
  accounting identities because the source presentation double-counts a parent
  and its “Trong đó” children.
- **BPA-001–BPA-003 — OPEN:** the VPB combined parent and two unsplit VIB
  use-purpose rows remain source-only rather than being forced into narrower
  security-class leaves.

## Customer collateral held (`CUSTOMER_COLLATERAL_HELD`)

Current exact-replay result:
`docs/experiments/E-0096-customer-collateral-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique customer-scoped region at VPB p67,
  VCB p47 and VIB p49. ACB/MBB/HDB/CTG/BID have no detailed customer-collateral
  note in the supplied reports.
- 15 mappings, 30 value cells and six child-to-parent equations are independently
  verified. VIB's separate TCTD and own-pledged-asset branches are excluded.
- **CC-001–CC-004 — CLOSED by E-0100:** project-owner adjudication aggregates
  each bank's source rows into 1288 `Khác` together with its pre-existing
  catch-all row, once only. Both VCB and VIB parent totals close exactly.

## State-budget obligations (`STATE_BUDGET_OBLIGATIONS`)

Current exact-replay result:
`docs/experiments/E-0095-state-budget-obligations-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p22, MBB p49,
  VPB p58, HDB p32, CTG p43, BID p26 and VIB p47; VCB has no detailed note in
  the supplied report.
- 33 mappings, 147 value cells and 37 roll-forward/net equations are
  independently verified. Thirteen visible dashes are retained as pixel-bound
  zeroes. VPB is explicitly Q1/2026.
- **SBO-001 — CLOSED by E-0100:** HDB `Tiền thuê đất` maps to 1279 `Các khoản
  phải nộp khác`; all five visible source cells are dashes and normalize to 0.

## Employee income (`EMPLOYEE_INCOME`)

Current exact-replay result:
`docs/experiments/E-0094-employee-income-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p26, VPB p66
  and VIB p49; MBB/HDB/VCB/CTG/BID have no detailed employee-income note in
  the supplied reports.
- 13 mappings, 26 value cells and 14 additive/ratio equations are independently
  verified. VPB is explicitly Q1/2026; VIB is the six-month period.
- **EI-001–EI-002 — CLOSED by E-0100:** the six-month source values are divided
  by exactly six and retained as rational numbers before mapping 1267/1268.

## Subsidiary acquisitions and disposals (`SUBSIDIARY_ACQUISITION_DISPOSAL`)

Current exact-replay result:
`docs/experiments/E-0093-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json`

- The shared whole-PDF graph requires total consideration, cash settlement and
  cash held by the acquired/disposed subsidiary, plus period and unit evidence.
- No supplied PDF contains that complete detail table. All eight outcomes are
  bounded absences with zero mappings and zero open source rows.
- **SAD-001–SAD-008 — confirmed bound-report absences:** HDB's HDS acquisition
  narrative and CTG's investment cash-flow captions remain explicit controls;
  they do not establish the three schema rows 1256–1258.

## Cash and cash equivalents (`CASH_EQUIVALENTS`)

Current exact-replay result:
`docs/experiments/E-0092-cash-equivalents-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p8, MBB p50,
  VPB p66, VCB p40, CTG p47 and VIB p45. It covers total-before-components,
  combined interbank, demand/term split and optional-securities layouts.
- 31 mappings, 60 value cells and 12 accounting equations are independently
  verified, covering ReportNormId 1248–1254. No source row remains open.
- **CEQ-001–CEQ-002 — confirmed bound-report absences:** HDB and BID have no
  detailed component table; their cash-flow beginning/end balances and policy
  text remain negative controls, not mappings.

## Corporate income tax expense (`INCOME_TAX`)

Current exact-replay result:
`docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique detailed reconciliation at MBB
  p50, VPB p59 and VIB p48, using profit before tax, adjustments, taxable
  income, current tax and period/unit topology rather than bank/page routing.
- 28 mappings, 56 value cells and 20 accounting equations are independently
  verified. The mapped union covers ReportNormId 5723–5737. VPB remains Q1.
- **TAX-001 — OPEN:** VIB p48 `Điều chỉnh khác`; current-period cell is blank,
  comparative value is `163`. The source meaning is broader than 5733, so it
  remains explicit and is used only in the comparative printed-total equation.
- **TAX-002–TAX-006 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no detailed tax reconciliation; statement totals, tax-obligation
  movements and deferred-tax balances are retained as negative controls.

## Other activity income, expense and net (`OTHER_ACTIVITY`)

Current exact-replay result:
`docs/experiments/E-0090-other-activity-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique numbered note at MBB p47, VPB
  p64 and VIB p46. It accepts a net-only variant or gross income/expense
  parents with optional children and labeled/unlabeled net totals, without
  using bank, filename, note number or page as a rule.
- 23 mappings, 46 value cells and 14 accounting equations are independently
  verified. VPB's two visible asset-disposal rows are summed by authenticated
  components before one mapping to 1231.
- **OACT-001 — CLOSED by E-0100:** VPB p64 values `41 / 9` are aggregated once
  into 1239 `Khác`; the income-parent and net equations remain exact.
- **OACT-002–OACT-006 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no complete numbered detail note with period/unit axes,
  components and net total. Their KQKD totals, segment reports and explanatory
  text remain negative controls.

## Credit-risk provision expense (`CREDIT_RISK_PROVISION_EXPENSE`)

Current exact-replay result:
`docs/experiments/E-0089-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique numbered detailed note at MBB
  p49, VPB p66 and VIB p47. It accepts wrapped labels, optional rows, a customer
  parent with general/specific children and an unlabeled trailing total without
  using bank, filename, note number or page as a rule.
- 15 mappings, 30 value cells and eight accounting equations are independently
  verified. Combined customer/TCTD/purchased-debt rows use existing schema
  6031/6032/6033 rather than creating duplicate concepts.
- **CRPE-001–CRPE-002 — CLOSED by E-0100:** the VPB margin/advance row
  (`- / 29.368`) and VIB trade-finance-receivable row (`- / (244)`) map to
  1228 `Dự phòng khác`; both printed family totals replay exactly.
- **CRPE-003–CRPE-007 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no complete detailed note with period/unit axes, component rows
  and trailing total in the supplied PDFs. Statement aggregates, policies and
  explanatory mentions remain negative controls and are not relabelled.

## Capital and funds (`CAPITAL_AND_FUNDS`)

Current exact-replay result:
`docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in all eight
  reports, including geometry-selected 90-degree VietOCR rescue for rotated
  layouts; 19 near regions remain negative controls.
- ACB/MBB/VPB/HDB/VCB/CTG have 65 verified mappings, 131 numeric components and
  20 exact accounting equations. The supplied VPB PDF remains Q1/2026.
- CAF-001–CAF-008 are exact source columns without one equivalent schema leaf.
  CAF-009–CAF-010 retain BID/VIB as structure-only until an independent rotated
  numeric challenger is available; rotated VietOCR is text evidence only.

## Other payables and liabilities (`OTHER_PAYABLES_AND_LIABILITIES`)

Current exact-replay result:
`docs/experiments/E-0077-other-payables-liabilities-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in every report
  and retains 36 near controls. It requires only the owner plus internal and
  external payable branches; employee, tax, other-payable, risk, welfare,
  interest/fee and intermediate branches remain optional.
- Exact visible-pixel/source-numeric replay verifies 39 schema mappings, 78
  current/comparative components and 28 parent/detail/total equations. Two ACB
  risk-provision dashes are pixel-bound and normalized to zero.
- E-0132A closes OPL-001–OPL-018 to 1127 `Khác` under the project-owner rule
  for source rows without a dedicated leaf. Their amounts remain inside verified
  source parents/totals, and overlapping parent/detail views stay explicitly
  non-additive. VPB remains the supplied Q1/2026 source.

## Issued valuable papers (`ISSUED_VALUABLE_PAPERS`)

Current exact-replay result:
`docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in each of the
  eight reports and retains 29 near controls. It covers vertical instrument/
  tenor tables, book-value versus face-value lanes, combined promissory/bond
  parents and horizontal instrument columns without bank/page routing.
- 66 mappings, 124 value components and 36 accounting equations are
  `VERIFIED_BY_CODEX`. Four CTG dash cells are bound to exact render pixels and
  normalized to zero; empty cells are not promoted to zero.
- E-0080 closes ACB exact-five-year rows through the now-inclusive 1103/1111
  boundaries, maps MBB's printed broad tenors directly to 6009/6010 without
  inventing a narrower split, and maps BID's capital-increase bond to 1117.
  IVP-005–IVP-007 remain open only because VPB prints one whole-family tenor
  view without an instrument allocation. VPB is retained as Q1/2026.

## Entrusted/investment-risk capital (`ENTRUSTED_INVESTMENT_RISK_CAPITAL`)

Current exact-replay result:
`docs/experiments/E-0075-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region at MBB p43,
  VPB p56 and VIB p42, with no second complete match. It admits an aggregate
  organization/person row, a two-line ODA source and a three-line NHNN housing
  programme without bank/page routing.
- Six mappings/12 current-comparative components are `VERIFIED_BY_CODEX`; four
  printed child-to-total equations at MBB/VPB close exactly. The two small
  source-specific rows map to explicit schema catch-all 1099 rather than being
  forced into a semantically narrower currency/international-organization leaf.
- ACB/HDB/VCB/CTG/BID are absent only within the supplied reports. There are no
  open source rows for this family. VPB remains Q1/2026.

## Government and central-bank liabilities (`GOVERNMENT_NHNN_LIABILITIES`)

Current exact-replay result:
`docs/experiments/E-0074-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in each of the
  eight reports and retains 17 near regions as negative controls. It admits an
  aggregate-only table, detailed central-bank facilities, Treasury currency or
  tenor branches, repo rows and other liabilities without bank/page routing.
- 28 source mappings, 58 visible current/comparative components and 28 exact
  accounting equations are `VERIFIED_BY_CODEX`. Two source dashes omitted from
  OCR are independently bound to render pixels and normalized to zero.
- E-0080 adds broad parent 6070 for the three central-bank-loan wording
  variants and sibling 6071 for the Treasury term deposit. BID's Finance
  Ministry deposit is reclassified from catch-all 1039 to dedicated 6072.
  No source row remains open; VPB is correctly retained as Q1/2026.

## Other assets (`OTHER_ASSETS`)

Current exact-replay result:
`docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json`

- Whole-PDF fresh-VietOCR scan finds exactly one complete region in each of
  MBB p42, VPB p51–53 and VIB p39; no document has a second complete match.
  The shared graph admits split sibling notes, an explicit multi-page umbrella
  and an integrated table with subtables without bank/page routing.
- 58 source mappings, 126 visible current/comparative components and 30 exact
  accounting equations are `VERIFIED_BY_CODEX`. Five supplied reports are
  bounded absences between their long-term-investment and government-liability
  note boundaries.
- OA-001–OA-012 retain every source row that lacks an equivalent schema or has
  a broader/narrower meaning. They remain at the top of the open queue while
  the family itself is closed at its safely mapped core.

## Investment property (`INVESTMENT_PROPERTY_MOVEMENT`)

Current exact-replay result:
`docs/experiments/E-0072-investment-property-8bank-codex-verified-mapping-v1.json`

- The shared fixed-asset engine scans all 453 pages, partitions same-page
  current/comparative regions by their explicit period ends, and finds only
  MBB p41 as one unique current detailed region. The 31/12/2025 table is retained
  as comparison evidence rather than mixed into the 30/06/2026 values.
- Nine source mappings and eleven visible roll-forward, asset-column and
  carrying-value equations are `VERIFIED_BY_CODEX`. MBB's `Giá trị hao mòn`
  wording is accepted as the accumulated-depreciation branch. The visible DASH
  in current cost increases is pixel-bound and normalized to zero.
- IP-001–IP-007 close the other seven outcomes only for these supplied PDFs.
  Balance-sheet lines, accounting policies, cash-flow rows and combined
  fixed-asset/investment-property expenses remain negative controls. No source
  row in the verified MBB region remains open.

## Intangible fixed assets (`INTANGIBLE_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0071-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json`

- One shared fixed-asset graph scans all 453 pages and finds unique current-period
  regions at MBB p39, VPB p50 and VIB p38; MBB p40 remains comparison-only.
- 32 source mappings and 12 visible roll-forward/carrying-value equations are
  `VERIFIED_BY_CODEX`. ReportNormId 6068 groups gross-cost decreases 921–927;
  new ReportNormId 6069 preserves the distinct fully-amortized-but-still-in-use
  disclosure at VPB/VIB rather than forcing it into another movement row.
- IFA-001–IFA-005 close the five no-region outcomes only for the supplied PDFs.
  IFA-006 closes the schema gap. No intangible-fixed-asset row remains open;
  VPB keeps its Q1/2026 source-period caveat.

## Customer-loan geography (`LOAN_GEOGRAPHIC_CLASSIFICATION`)

Base exact-replay result:
`docs/experiments/E-0065-loan-geography-8bank-codex-verified-mapping-v1.json`

Project-owner absence closure:
`docs/experiments/E-0067D-loan-geography-project-owner-absence-closure-v1.json`

- One bank-blind graph scans all 453 pages and combines the geographic
  concentration heading with an exact customer-loan axis before reading the
  domestic/foreign structure. It supports geography by rows or columns and
  consecutive-period continuation, while retaining broader total-loan tables
  and geographic segment reports as negative controls.
- MBB p52 and VIB p53–54 are the only exact customer-loan populations. Four
  source rows (5752/765 for each bank), six period-value cells and three
  domestic-plus-foreign equations are `VERIFIED_BY_CODEX`. VIB's two visible
  foreign dashes stay typed `DASH` before zero normalization.
- LG-001–LG-006 are closed as bound-report absences for this exact family.
  ACB/VPB/HDB/CTG/BID retain their mechanically broader total-loan geography
  equations as negative controls; VCB retains its p42 segment-report matrix.
  None is silently narrowed, promoted, or treated as absent in another filing.

## Deposits at and loans to other credit institutions (`INTERBANK_DEPOSITS_AND_LOANS`)

Current all-filing artifacts:
`output/calibration/family-first-accounting-evidence-sweeps-v1/interbank-deposits-and-loans.json`
and
`output/calibration/family-first-accounting-schema-mappings-v1/interbank-deposits-and-loans.json`.

- **OPEN — ACB (10 filing):** annual-2025 consolidated p7/p46 and H1-2025
  consolidated p7/p45 contain both a summary and detailed region headed
  `Tiền gửi và cho vay các TCTD khác`; neither candidate has a fully bound
  column/body axis. Q1/Q4-2025 and Q1/Q2-2026, both scopes, p15–16 retain the
  same owner but one or more visible role rows lack a complete two-lane axis.
- **OPEN — MBB (2 filing):** Q1-2025 consolidated p29 and parent p26,
  `Tiền gửi và cho vay các TCTD khác`; the printed deposit/family result differs
  from the exact component population currently bound. Source values are not
  repaired to force closure.
- **OPEN — VPB (4 filing):** annual-2025 and H1-2025, both scopes, p42/p36 and
  p44/p36, owner `Tiền gửi và cấp tín dụng cho các TCTD khác`; one or more role
  rows lack a complete visible lane axis.
- **OPEN — HDB (10 filing):** annual-2025 both scopes p34/p33 and Q3-2025 both
  scopes p3 have incomplete visible role lanes; H1-2025 p31/p30 has a trailing
  result that is not one exact family-component sum; Q1/Q2-2025, both scopes,
  p3 has a printed `Cho vay các TCTD khác` result that does not equal the
  visible component population. The owner is `Tiền gửi tại và cho vay các
  TCTD khác`.
- **OPEN — CTG (3 filing):** annual-2025 parent p39 lacks proven cross-page
  period/unit inheritance; H1-2025 parent p11/p21 has two competing regions;
  Q1-2025 consolidated p4 has an interbank-loan result that does not equal the
  visible component population. Source owner: `Tiền gửi và cho vay các TCTD
  khác`.
- **OPEN — BID (1 filing):** H1-2025 consolidated p9, `Tiền gửi và cho vay các
  TCTD khác`; the trailing result is not one exact sum of the bound family
  components.
- **OPEN — VIB (12 filing):** annual-2025 parent, H1-2025 both scopes,
  Q1-2025 both scopes, Q2-2025 parent, Q3/Q4-2025 both scopes and Q2-2026 both
  scopes contain both summary and detailed regions headed `Tiền gửi và cho vay
  các TCTD khác`. Pages are respectively p9/p37, p9–10/p37–38, p9–10/p37,
  p5/p32, p8–9/p36–37, p5/p32–33 and p5/p32. Header/body geometry or complete
  role lanes do not yet choose one region uniquely; no bank/page routing is
  used to break the tie.
- **CLOSED COUNTS:** 84/140 filing and 701 source mappings are
  `VERIFIED_BY_CODEX`; 14 filing are `NOT_OBSERVED_PROPOSAL_ONLY` (BID 12,
  CTG 2); the 42 filing above remain `UNRESOLVED`.

## Deposits at central banks (`CENTRAL_BANK_DEPOSITS`)

Current exact-replay result:
`docs/experiments/E-0061-central-bank-deposits-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and binds the first family owner,
  central-bank parent, required currency children and first trailing two-period
  total. It records horizontal row/period layout and stops before reserve-ratio
  tables or the next TM family.
- MBB p30, VPB p38 and VIB p31 are the only unique complete detailed clusters.
  Ten source rows are `VERIFIED_BY_CODEX`, and four current-period equations
  close exactly. VPB retains its Q1/2026 source-period caveat.
- MBB's Laos and Cambodia rows are aggregated into ReportNormId 574 `Tiền gửi
  khác`: `934.855 + 1.213.504 = 2.148.359`; together with Vietnam deposits,
  `25.269.011 + 2.148.359 = 27.417.370`. The project owner
  confirmed that ACB/HDB/VCB/CTG/BID do not contain this TM family in the bound
  PDFs, based on each report's first TM family boundary; balance-sheet totals
  do not contradict that bounded note-level absence.

## Cash and precious metals (`CASH_PRECIOUS_METALS`)

Current exact-replay result:
`docs/experiments/E-0060-cash-precious-metals-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and requires a short owner, VND and
  foreign-currency cash children, visible period/unit axes and a trailing total.
  It finds exactly one complete region for MBB p30, VPB p38 and VIB p31.
- 12 source rows are `VERIFIED_BY_CODEX`: ReportNormId 562, 563, 565 and the
  exact family total 561 for each complete region. Three current-period
  `VND + foreign + monetary gold = total` equations close exactly.
- The project owner confirmed ACB/HDB/VCB/CTG/BID do not contain this TM family
  in the bound PDFs: ACB's notes start at the interbank family, while the other
  four start at trading securities. Balance-sheet totals and cash-flow/risk
  disclosures remain negative controls rather than manufactured note mappings.
- VPB retains its Q1/2026 source-period caveat.

## Trading securities (`TRADING_SECURITIES`)

Current exact-replay result:
`docs/experiments/E-0059-trading-securities-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages. It finds one unique trading region
  for ACB, MBB, VPB, HDB, VCB, CTG and BID, while rejecting accounting-policy
  prose, provision roll-forwards and investment securities as sibling families.
- 58 source rows are `VERIFIED_BY_CODEX`; 20 parent/child and
  gross/provision/net equations close exactly. First/last cluster items, PDF row
  order, period/unit columns and parent-total placement remain explicit.
- MBB uses the listed/unlisted branch. The other six mapped banks use the issuer
  branch. Unlabeled gross rows are admitted only when topology and the full
  accounting equation both agree.
- VIB p36 AFS was deliberately excluded here and is now resolved by E-0067 as
  the investment-securities family. VPB retains its Q1/2026 source-period caveat.

## Investment securities (`INVESTMENT_SECURITIES`)

Base exact-replay result:
`docs/experiments/E-0067-investment-securities-8bank-codex-verified-mapping-v1.json`

Project-owner closure:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- One bank-blind graph scans all 453 pages and finds exactly one complete
  investment region per PDF. It supports explicit or implicit family owners,
  AFS/HTM branches, provision and quality alternate views, VAMC, two-page
  continuation and first/last/next-family boundaries.
- ACB p19, MBB p35–36, VPB p47–48, HDB p29, VCB p32, CTG p40, BID p23 and
  VIB p36 now provide 99 verified source mappings/198 period cells; 39 visible
  parent-child or gross-provision-net equations close exactly.
- IS-001 is closed by the explicit document-level `Triệu VND` statement on BID
  p13 of the same PDF. IS-002 is closed by retaining both VIB source components
  and proving `5.894.320 + 32.879.230 = 38.773.550` and
  `12.104.102 + 28.252.422 = 40.356.524` before mapping one aggregate to 808.

## Other long-term investments (`OTHER_LONG_TERM_INVESTMENTS`)

Current exact-replay result:
`docs/experiments/E-0068-long-term-investments-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and finds exactly one complete
  region in each PDF: ACB p19, MBB p36, VPB p48, HDB p30, VCB p33, CTG p40,
  BID p24 and VIB p36. Optional joint-venture, associate, other-investment,
  organization/project and fund branches may be absent or reordered.
- All 29 reviewed source mappings and 58 period cells are
  `VERIFIED_BY_CODEX`; nine visible accounting equations close exactly. The
  HDB current associate DASH remains typed before zero normalization. VPB
  remains explicitly Q1/2026.
- Schema gaps for joint ventures and associates are closed by ReportNormId
  6066 and 6067 under parent 862. No source row from the bounded eight regions
  remains in the open queue; detailed organization rows are retained as
  corroboration and are not double-counted with their mapped parent.

## Tangible fixed assets (`TANGIBLE_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0069-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json`

- One bank-blind owner/cost/accumulated-depreciation/carrying-value graph scans
  all 453 pages and finds unique detailed regions at MBB p37, VPB p49 and VIB
  p37. MBB p38 is retained only as the prior-period continuation control.
- All 35 reviewed mappings and 12 visible roll-forward/carrying-value equations
  are `VERIFIED_BY_CODEX`. VIB's rotated page uses fresh same-model VietOCR for
  text and an independently sealed rotated PP-OCRv6 numeric challenger; four
  disagreements from the original rotated source OCR are resolved by pixels and
  exact accounting closure rather than semantic guessing.
- ACB/HDB/VCB/CTG/BID are confirmed absent only in the bound reports. Main
  statement balances and accounting-policy prose remain negative controls.
  There is no open mapping item for this family. VPB remains Q1/2026.

## Leased fixed assets (`LEASED_FIXED_ASSETS_ROLLFORWARD`)

Annual-2025 exact-replay result:
`docs/experiments/E-0124-annual-2025-leased-fixed-assets-8bank-bound-report-absence-v1.json`

- The reporting-period-general graph scans all eight audited consolidated
  annual-2025 PDFs, including split owner/branch lines and the complete rotated
  VietOCR rescue denominator. It finds zero complete and zero near 896–912
  regions. The automatically selected tangible→intangible boundaries are ACB
  p55→56, MBB p58→60, VPB p53→54, HDB p41→42, VCB p48→49, CTG p48→49, BID
  p47→48 and VIB p42→43.
- Thirty finance-lease company, policy, lending and income lines remain exact
  negative controls. No source row is OPEN and no mapping is manufactured.
  The family-local schema projection is insensitive to unrelated global schema
  insertions; live ReportNormId/name/parent compatibility is still required.

Current exact-replay result:
`docs/experiments/E-0070-leased-fixed-assets-8bank-bound-report-absence-v1.json`

- The shared fixed-asset graph scans all 453 pages and finds no complete or
  near-complete 896–912 region in ACB, MBB, VPB, HDB, VCB, CTG, BID or VIB.
- All eight dispositions are `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; this is
  bounded to the supplied PDFs and is not a broader bank/document absence
  claim.
- Twenty-four finance-lease company, policy, lending and income lines remain
  negative controls. No source row is open and no mapping is manufactured.

## Project-owner TM adjudications

Exact-replay decision artifact:
`docs/experiments/E-0067A-project-owner-tm-adjudications-v1.json`

- CBD-001/CBD-002 close into one ReportNormId 574 aggregate with exact source
  components and arithmetic retained.
- IDL-001/IDL-002 and DFI-001 close as bounded-report absences; the confirmation
  does not assert absence in another filing or bank.
- VIB p36 is explicitly confirmed under 804 → 805, with the live 804 children
  805/829/853/859 and last descendant 861; it is not trading 592.

## Loan-quality margin normalization

Exact-replay normalized result:
`docs/experiments/E-0067B-loan-quality-margin-separation-project-owner-v1.json`

- The already registered template identity 1944 is reused instead of allocating
  another duplicate-name ID. In this bounded context it is a direct child of
  family 746 and represents `Cho vay giao dịch ký quỹ và ứng trước tiền bán
  chứng khoán` independently from the five quality grades.
- ACB p18 and VPB p42 expose the row after the five-grade core, so ReportNormId
  747 remains unchanged and the visible row maps to 1944.
- MBB p31 exposes the same population as 5746 `Trong đó` under 747. The source
  disclosure is retained as a non-output bridge; normalized 747 is reduced by
  exactly 5746 on both axes and the same amount is emitted once as 1944.
- All 18 per-axis family/split equations close; no 5746+1944 double count is
  permitted. This closes the two former outside-core ACB/VPB populations.

## Customer-deposit and investment owner closure

Exact-replay result:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- CD-001/CD-002: the two-state-member-or-more labels at VPB p55 and VIB p42
  map to the owner-confirmed schema 770 name `Công ty TNHH MTV (hoặc trên MTV)
  vốn nhà nước trên 50%`; values `64.165` and `174` remain separately bound.
- IS-001: BID p23 inherits `Triệu VND` only from the visible document-level
  declaration at p13 of that same PDF. Fourteen mappings, 28 cells and ten
  accounting equations are independently replayed; the visible comparative
  dash remains typed before zero normalization.
- IS-002: VIB p36 retains the bond and certificate-of-deposit components and
  maps their per-period sums once to 808. No component is dropped or emitted a
  second time.

## Customer deposit (`CUSTOMER_DEPOSIT_CLASSIFICATION`)

Base exact-replay result:
`docs/experiments/E-0058-customer-deposit-8bank-codex-verified-mapping-v1.json`

Project-owner closure:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- Một graph bank-blind quét đủ 453 trang và tìm đúng một vùng hoàn chỉnh trong
  mỗi PDF. Biên đầu/cuối, thứ tự hàng nguồn, bố cục ngang/dọc, kỳ và trục tiền tệ
  đều được giữ lại.
- 120 dòng được xác minh; 43 phương trình cha = con, tổng cột và tổng
  bảng đóng chính xác. Cột tổng và cột phần trăm chỉ là đối chứng khi không phải
  một khoản mục độc lập.
- VIB p42 dòng `Công ty Nhà nước`: VietOCR Transformer đọc thiếu chữ số đầu
  (`3.034.518`), còn pixel PDF và numeric challenger PP-OCRv6 cùng cho
  `13.034.518`; kết quả dùng `13.034.518` và lưu nguyên disagreement.
- CD-001/CD-002 đã đóng: hai dòng VPB/VIB cùng map vào schema 770 theo quyết
  định của chủ dự án, giữ nguyên giá trị nguồn `64.165` và `174`. Không còn
  dòng nguồn chưa map trong family; VPB vẫn giữ đúng kỳ nguồn Q1/2026.

## Provision movement (`PROVISION_MOVEMENT_ROLLFORWARD`)

Annual-2025 exact-replay result:
`docs/experiments/E-0119-annual-2025-provision-movement-8bank-codex-verified-mapping-v1.json`

- ACB p51, MBB p53, VPB p48, HDB p38, VCB p41, CTG p44, BID p43 và VIB p39:
  `VERIFIED_BY_CODEX` cho đúng roll-forward 2025 của BCTC hợp nhất kiểm toán.
- 18 lane cha, 79 movement rows, 18 phương trình và chín DASH→0 đều đã đóng;
  không còn dòng OPEN trong family annual-2025.
- ACB/VPB map riêng margin/ứng trước 6061–6065. Cột tổng, địa lý và deferred-LC
  chỉ làm đối chứng, không xuất cộng trùng.

Kết quả kỳ hiện hành trước đó vẫn giữ riêng tại:
`docs/experiments/E-0057-provision-movement-8bank-codex-verified-mapping-v1.json`

- ACB p18, MBB p34, HDB p28, VCB p31, CTG p39, BID p23 và VIB p34:
  `VERIFIED_BY_CODEX` cho kỳ hiện tại Q2/2026.
- VPB p45: `VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT` cho kỳ
  01/01–31/03/2026. Ba lane chung/cụ thể/margin-ứng trước và toàn bộ movement
  hiện hữu đều đã map; chỉ nguồn Q2/2026 còn thiếu.
- MBB chỉ dùng cột `Tổng cộng`; các cột Việt Nam/nước ngoài là đối chứng.
  Kỳ so sánh của mọi bank không được dùng làm mapping authority.

## OCR and numeric evidence policy

- Vietnamese semantic anchors come from the fresh VietOCR Transformer cache;
  accentless normalization and bounded edit-distance matching only locate a
  candidate graph.  They never decide the mapping by themselves.
- PP-OCRv6 is an authenticated geometry/provider and may contribute an
  independent numeric proposal.  It is **not**, by itself, final numeric truth.
- Gemma is permitted only as a bounded rescue/challenger on a fixed difficult
  crop.  A Gemma answer cannot silently replace a digit, sign, decimal separator,
  DASH, blank, or missing cell and cannot become automatic numeric authority.
- An accepted number must remain bound to the exact crop and typed lane, survive
  independent digit/sign/DASH review, and satisfy the applicable row/total/
  roll-forward accounting equations.  Disagreement without decisive pixel and
  accounting evidence remains `UNRESOLVED`.

## Loan type (`LOAN_TYPE_CLASSIFICATION`)

Historical pre-adjudication result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v1.json`

Current exact-replay result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v2.json`

Result ID:
`lt8bcv2:result:f5765671514ac40550fe349633b2d95b693537d65e18e91101434904d3d652dd`

### LT-001 — ACB — government-directed lending

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 17 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cho vay theo chỉ định của Chính phủ`
- Visible source values: `-` / `-`; raw source status remains `DASH`.
- Project-owner decision: append an exact schema child for the visible label and
  normalize each independently reviewed visible DASH to numeric `0` for the
  template without erasing the raw DASH provenance.
- Accepted schema: ReportNormId `6057` (`Cho vay theo chỉ định của Chính phủ`),
  parent `717`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LT-002 — VPB — other credit

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 42 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cấp tín dụng khác`
- Visible values: `72.360.147 | 6,95% | 73.847.196 | 7,82%`
- Accepted schema: ReportNormId `726` (`Cho vay khác`).
- Project-owner decision: within this exact `Cho vay khách hàng` type-analysis
  graph, `Cấp tín dụng khác` is the source variant of `Cho vay khác`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

## Loan industry (`LOAN_INDUSTRY_CLASSIFICATION`)

Source scan: `lifdsv1:scan:a0b560c0ff0fb07fff7e49e4c9b38c2b3f9baa8aefb9d911f37d01a920b54a11`

Historical pre-adjudication result ID:
`li8bcv1:result:a7435794e8639f9aa53ada040d13abddf966b91ab839a9aa1391bf2cdba52c58`

Current exact-replay result:
`docs/experiments/E-0055-loan-industry-8bank-codex-verified-mapping-v2.json`

Current result ID:
`li8bcv2:result:3ac4ba987593baf8e0a03c3a1f2414dacf1008df38fc890519d72d2c9160cbdb`

Exact-replay builder:
`scripts/experiments/build_loan_industry_8bank_codex_verified_mapping_v1.py`

### LI-001 — ACB — industry family not present in bound report

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 33 physical pages, fresh VietOCR line axis
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Machine scan: no region survives the full-PDF parent/child-pair search plus
  period/unit/total/accounting checks; trying a smaller one-child graph does not
  manufacture an occurrence.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; this is not a claim about
  other ACB reports or the broader corpus.

### LI-002 — MBB — transport and storage

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải, Kho bãi`
- Visible values: `34.348.471 | 2,80% | 29.961.714 | 2,76%`
- Accepted schema: ReportNormId `736` (`Vận tải kho bãi và thông tin liên lạc`).
- Project-owner decision: `Vận tải, Kho bãi` is an admitted source variant of
  the combined schema concept; the separately visible information/communication
  row remains mapped to its own ReportNormId `740`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-003 — MBB — foreign branch population

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Visible values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Accepted schema: new ReportNormId `6058`, exact visible-label child under
  ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-004 — VPB — transport and storage

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải kho bãi`
- Visible values: `12.790.970 | 1,23% | 12.417.698 | 1,32%`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-005 — VPB — public administration/defence/social security

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Hoạt động của Đảng cộng sản, tổ chức chính trị-xã hội, quản lý Nhà nước, an ninh quốc phòng, bảo đảm xã hội bắt buộc`
- Visible values: `5.892 | 0,00% | 14.165 | 0,00%`
- Accepted schema: ReportNormId `745` (`Các ngành nghề khác`).
- Project-owner decision: this immaterial row is grouped into the explicit
  catch-all; it is not mapped to ReportNormId `744`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-006 — VPB — personal housing loan population

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở`
- Visible values: `139.410.297 | 13,39% | 130.375.600 | 13,81%`
- Accepted schema: new ReportNormId `6059`, exact visible-label child under
  ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-007 — HDB — transport and storage

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 27 / `Phân tích dư nợ cho vay theo ngành nghề đăng ký kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `26.889.305 | 25.142.909`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-008 — VCB — industry family not present in bound report

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 55 physical pages, fresh VietOCR line axis (including terminal
  geometry-only pages without inherited transcript)
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry; the visible loan analysis on page 31 is by maturity, not industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; no broader-corpus absence
  claim is made.

### LI-009 — CTG — industry family not present in bound report

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 61 physical pages, fresh VietOCR line axis
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry; the visible loan analysis on page 39 is by original loan tenor, not
  industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; no broader-corpus absence
  claim is made.

### LI-010 — BID — broad services

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 22 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Dịch vụ`
- Visible values: `534.960.928 | 444.190.319`
- Accepted schema: new ReportNormId `6060` (`Dịch vụ`), exact visible-label
  child under ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-011 — VIB — transport and storage

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ theo ngành nghề kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `11.771.262 | 2,96% | 12.478.803 | 3,27%`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

## Loan enterprise/customer type (`LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION`)

Fresh full-document scan:
`lefdsv1:scan:a8d2c5c3b49051773ca518a793a407ace5d9d9e2397675398f20f703143958d6`

Current exact-replay result:
`docs/experiments/E-0056-loan-enterprise-8bank-codex-verified-mapping-v1.json`

Result ID:
`le8bcv1:result:b6b858689f966259c4b2c8b4ea91bcc7c6bec906ce3cd060df9ebcb3eb5f27a9`

The enterprise/legal-form matcher found one unique complete region in MBB p32,
VPB p43, HDB p26, and VIB p34.  The other four PDFs do not expose that legal-form
branch, but each contains a distinct headerless **loan-type** region directly
under `Cho vay khách hàng`; those regions are already found and verified by the
owner-direct E-0054 graph.  They are not forced into the wrong schema parent
766.  In E-0056, 44 source rows are `VERIFIED_BY_CODEX`, including the exact
foreign-branch population concept 6058; no schema-semantic row remains
unresolved.  Six non-additive source group/total equations remain explicit.

### LE-001 — ACB — headerless owner-direct loan-type region

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 17, directly below `4. CHO VAY KHÁCH HÀNG:`.
- No branch title `Phân tích theo loại hình cho vay` is required.  The generic
  owner-direct graph binds the two period axes, unit scope, seven visible child
  roles and the closing total.
- Verified children include ReportNormIds `718`, `722`, `719`, `723`, `725`,
  `721`, and `724`; government-directed lending is separately mapped to `6057`.
- Resolving result: E-0054 V2
  `lt8bcv2:result:f5765671514ac40550fe349633b2d95b693537d65e18e91101434904d3d652dd`.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-002 — MBB — source-only “Cho vay các TCKT” group parent

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 32 / enterprise or customer-type analysis
- Pixel text / accentless: `Cho vay các TCKT` / `cho vay cac tckt`
- Visible values: `721.497.618 | 58,79% | 621.056.253 | 57,28%`
- Candidate schema: no new leaf is needed.  The visible legal-form descendants
  remain the higher-resolution representation.
- Review status: `RESOLVED_SOURCE_ONLY_GRAPH_NODE_RETAINED_FOR_CHECK`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_WOULD_DOUBLE_COUNT_LEGAL_FORM_CHILDREN`
- Reason: its visible legal-form descendants already partition and sum to this
  parent. Mapping both parent and descendants would double count.
- Resolution: retained as a source-only graph parent; its two-axis parent-child
  equation is replayed and closed in the E-0056 result.

### LE-003 — MBB — source-only “Cho vay cá nhân” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay cá nhân` / `cho vay ca nhan`
- Visible values: `478.995.719 | 39,01% | 437.686.958 | 40,38%`
- Accepted schema equivalence: ReportNormId `780` (`Hộ kinh doanh, cá nhân`).
- Review status: `RESOLVED_NON_ADDITIVE_SCHEMA_EQUIVALENCE`
- Resolution: `Cho vay cá nhân` and its immediately following 780 child have
  identical four-lane values.  E-0056 records the parent→780 equivalence but
  exports the numeric amount once only; parent and child must never be summed.

### LE-004 — MBB — source-only “Cho vay khác” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay khác` / `cho vay khac`
- Visible values: `937.382 | 0,08% | 904.945 | 0,09%`
- Accepted aggregate equivalence: ReportNormId `782` (`Khác`).
- Review status: `RESOLVED_NON_ADDITIVE_SCHEMA_EQUIVALENCE`
- Resolution: the source parent is explicitly associated with 782 as the
  aggregate/catch-all view, while its two visible children remain available as
  the detailed view.  E-0056 marks the relation non-additive, so an export must
  choose the aggregate or its descendants and cannot count both.

### LE-005 — MBB — foreign-branch population and its two children

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel parent: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Parent values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Pixel children: `Cho vay Doanh nghiệp` = `2.121.916 / 2.176.885`;
  `Cho vay cá nhân` = `7.173.788 / 7.153.744`
- Accepted schema: ReportNormId `6058`, whose canonical label is already exactly
  `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`.
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Resolution: the project reuses the existing exact concept rather than creating
  a duplicate ID merely because MBB repeats it in another source presentation.
  E-0056 maps the row once, preserves its two source children and parent-child
  equation, and marks the group relation non-additive.

### LE-006 — VPB — “Khác” monetary cells not attached by semantic geometry

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 43 / enterprise or customer-type analysis
- Pixel text / accentless: `Khác` / `khac`
- Raw VietOCR values: `2 | 0,00 | 2 | 0,00`
- Graph values: `missing | 0,00 | missing | 0,00`
- Candidate schema: ReportNormId `782`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `VISIBLE_MONETARY_CELLS_OUTSIDE_CURRENT_ROW_GEOMETRY_BAND`
- Reason: pixels clearly show both monetary values, but the current generic row
  association did not bind them. No zero/missing imputation is allowed.
- Resolution: exact visible monetary cells `2 / 2` are pixel-bound, close the
  accounting graph, and map to ReportNormId `782` (`Khác`).

### LE-007 — HDB — “Doanh nghiệp tư nhân” dash/current and 27/comparative

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 26 / enterprise or customer-type analysis
- Pixel text / accentless: `Doanh nghiệp tư nhân` / `doanh nghiep tu nhan`
- Pixel values: `- | 27` (`DASH`, not zero or missing)
- Fresh semantic graph values: `missing | 27`
- Candidate schema: ReportNormId `774`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `DASH_PIXEL_NOT_PRESENT_IN_FRESH_SEMANTIC_LINE_AXIS`
- Reason: the row identity is structurally clear, but the numeric verifier must
  preserve a typed dash rather than treating the absent OCR token as zero.
- Resolution: the raw value remains typed `DASH`, while its explicit normalized
  numeric interpretation is `0`; the comparative `27` is preserved. The row maps
  to ReportNormId `774`.

### LE-008 — VCB — headerless owner-direct loan-type region

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 30, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `722`, `719`, `723`, and `721` without
  requiring a printed branch title.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-009 — CTG — headerless owner-direct loan-type region

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 38, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `722`, `719`, `723`, `725`, `721`, and
  `726`; the visible DASH in `Cho vay khác` remains typed DASH with numeric
  interpretation zero.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-010 — BID — headerless owner-direct loan-type region

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 22, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `721`, `722`, `719`, and `723` plus the
  exact two-axis total.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-011 — VIB — VietOCR dropped one digit in “Công ty cổ phần khác”

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 34 / enterprise or customer-type analysis
- Label / accentless: `Công ty cổ phần khác` / `cong ty co phan khac`
- Raw VietOCR current value: `97.043.85`
- Independent PP-OCRv6 proposal: `97.043.851` with recognition score
  `0.9999531507492065`; this is corroborating numeric evidence, not sole truth.
- Independent pixel transcription: `97.043.851`
- Other visible lanes: `24,44% | 77.496.641 | 20,29%`
- Candidate schema: ReportNormId `773`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `FRESH_VIETOCR_DIGIT_OMISSION_BREAKS_CURRENT_PERIOD_ACCOUNTING_CLOSURE`
- Reason: the pixel value closes the printed total `397.083.447`; the raw OCR
  value does not. The correction must come from independent pixel-bound numeric
  verification, never silent string repair.
- Resolution: the exact crop-bound pixel value `97.043.851` is retained alongside
  the raw Transformer proposal and maps to ReportNormId `773`; total closure is exact.

## E-0066 / E-0120 — bounded whole-PDF controls for `Hoạt động mua nợ`

E-0120 repeats the complete-PDF scan on the eight audited consolidated
annual-2025 filings. It maps MBB p54, VPB p49, HDB p39 and VIB p40 with 15
schema rows, 30 cells and 19 exact equations. HDB's legitimate source variant
has no separate interest row, so 5739 is not fabricated. Five visible dashes
remain typed before zero normalization. These four entries are not open
mappings: the family is absent only inside each fixed supplied-PDF scope.

### PD-001 — ACB — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no region contains the owner `Hoạt động mua nợ`, the
  balance rows, the principal/interest detail and the next-family boundary.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-002 — VCB — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-003 — CTG — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-004 — BID — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

Resolving result: E-0066
`e0066:result:79e15086c88ca9283d450955da737a620012679f36071e39dce9a63962c76a3b`.

Annual-2025 resolving result: E-0120
`annual2025pd8bcv1:result:6c91fc19548f1ff71df439cf2d027d65e797aeb2c8f2a51b4776a732610909d2`.

## E-0157 — annual-2025 `Rủi ro thanh khoản`

- Review status: `RESOLVED_VERIFIED_BY_CODEX_NO_ANNUAL_OPEN_ROWS`.
- All eight audited consolidated annual-2025 PDFs contain one unique liquidity
  table. E-0157 verifies 181 mappings/181 cells and 54 exact equations; nine
  visible dashes are pixel-authenticated before normalization to zero.
- No annual-2025 source row remains in this ledger. The historical Q1/2026 VPB
  residuals LRISK-002–LRISK-005 remain attached only to that older filing and
  are not silently rewritten by the annual result.
- Result:
  `annual2025lrr8bcv1:result:671984613ccb960a8f1c491fc6b828c6b1b1e3544c7da5283be7c2fb34731b27`.

## E-0158 — annual-2025 `Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo`

- Review status: `OPEN_SCHEMA_GAPS_SOURCE_VALUES_VERIFIED`.
- MBB p103, VPB p98, HDB p69, CTG p85, BID p70 và VIB p77 là sáu vùng
  unique; ACB/VCB là hai bounded detailed-table absences. E-0158 xác minh
  55 mapping/110 ô schema trên tổng 74 hàng/148 ô nguồn.
- Xung đột duy nhất HDB/NZD comparative giữ cả VietOCR `14.382` và trục
  nguồn `14.362`; Gemma 4 crop-bound đọc `14.362`. Đây là challenger độc
  lập, không phải numeric truth và không tạo quy tắc sửa số tổng quát.
- Result:
  `annual2025fxrate8bcv1:result:add0abc2a953baa5115e0cbc881c654c681dea5e537350e4b3adbee4aca76c23`.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| AFXRATE-001 | VPB | 98 | CNY | Chưa có leaf CNY dưới schema 5935–5945. |
| AFXRATE-002 | VPB | 98 | DKK | Chưa có leaf DKK dưới schema 5935–5945. |
| AFXRATE-003 | VPB | 98 | NZD | Chưa có leaf NZD dưới schema 5935–5945. |
| AFXRATE-004 | VPB | 98 | XAU | Chưa có leaf vàng/XAU dưới schema 5935–5945. |
| AFXRATE-005 | HDB | 69 | CNY | Chưa có leaf CNY dưới schema 5935–5945. |
| AFXRATE-006 | HDB | 69 | HKD | Chưa có leaf HKD dưới schema 5935–5945. |
| AFXRATE-007 | HDB | 69 | KRW | Chưa có leaf KRW dưới schema 5935–5945. |
| AFXRATE-008 | HDB | 69 | NZD | Chưa có leaf NZD dưới schema 5935–5945. |
| AFXRATE-009 | CTG | 85 | NZD | Chưa có leaf NZD dưới schema 5935–5945. |
| AFXRATE-010 | CTG | 85 | NOK | Chưa có leaf NOK dưới schema 5935–5945. |
| AFXRATE-011 | CTG | 85 | DKK | Chưa có leaf DKK dưới schema 5935–5945. |
| AFXRATE-012 | CTG | 85 | HKD | Chưa có leaf HKD dưới schema 5935–5945. |
| AFXRATE-013 | CTG | 85 | CNY | Chưa có leaf CNY dưới schema 5935–5945. |
| AFXRATE-014 | CTG | 85 | KRW | Chưa có leaf KRW dưới schema 5935–5945. |
| AFXRATE-015 | CTG | 85 | LAK | Chưa có leaf LAK dưới schema 5935–5945. |
| AFXRATE-016 | VIB | 77 | DKK | Chưa có leaf DKK dưới schema 5935–5945. |
| AFXRATE-017 | VIB | 77 | HKD | Chưa có leaf HKD dưới schema 5935–5945. |
| AFXRATE-018 | VIB | 77 | NOK | Chưa có leaf NOK dưới schema 5935–5945. |
| AFXRATE-019 | VIB | 77 | XAU | Chưa có leaf vàng/XAU dưới schema 5935–5945. |

## E-0159 — annual-2025 `Tiền, vàng gửi và vay các TCTD khác` — nguồn vốn

- Review status: `OPEN_TWO_SOURCE_ONLY_AUXILIARY_ROWS`.
- ACB p61, MBB p64, VPB p58–59, HDB p44, VCB p52, CTG p51, BID p50 và
  VIB p45 là tám vùng unique. E-0159 xác minh 95 mapping/190 ô schema và
  40 phương trình dưới đúng root nguồn vốn 1040; family tài sản 575 là đối
  chứng âm và không được dùng chung mapping authority.
- Hai xung đột OCR số HDB đã được giải quyết bằng pixel, trục số nguồn và
  closure kế toán; chúng không phải dòng OPEN. Gemma 4 chỉ đọc lại hai crop
  làm challenger, không thay thế numeric authority.
- Result:
  `annual2025if8bcv1:result:0678d0d0bc4feaf02d5f6fbb72d6c744b29d8086f0449578931c3af698053395`.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| AIFUND-001 | VPB | 59 | Vốn vay từ Công ty Tài chính Quốc tế (IFC) | Chi tiết source-only, không cộng thêm vào subtotal vay và chưa có leaf chính xác dưới 1040–1052. |
| AIFUND-002 | HDB | 44 | Phải trả về nghiệp vụ UPAS LC | Parent trung gian chưa có leaf chính xác; hai dòng VND/ngoại tệ của nó đã được cộng đúng một lần vào aggregate vay 1049/1052, không map thêm parent. |

## E-0160 — annual-2025 `Kinh doanh và đầu tư chứng khoán` — khu vực địa lý

- Review status: `RESOLVED_VERIFIED_BY_CODEX_NO_ANNUAL_OPEN_ROWS`.
- ACB p77, MBB p91, VPB p81, HDB p60, BID p63 và VIB p59–60 có đúng một
  vùng hoàn chỉnh; 12 mapping/18 ô và 15 phương trình được xác minh. Năm dấu
  `-` có bbox pixel riêng trước khi chuẩn hóa về 0.
- VCB và CTG không có vùng thuyết minh hoàn chỉnh trong hai PDF đã bind. Các
  trang báo cáo bộ phận gần giống được giữ làm đối chứng âm, không map.
- Không còn dòng nguồn annual-2025 nào của family 5759–5761 trong ledger.
- Result:
  `annual2025sg8bcv1:result:5d80cb90d755c6b8ed1267a1fd640d1d2f959f62910eda3268e669633d7ae965`.

## E-0161 — annual-2025 `Báo cáo bộ phận hợp nhất`

- Review status: `OPEN_SOURCE_VARIANTS_WITH_SUPPORTED_SUBSET_VERIFIED`.
- Whole-PDF scan tìm đúng một vùng báo cáo bộ phận trong cả tám BCTC. Phần
  schema hỗ trợ đã được xác minh qua 73 binding cấu trúc, 208 mapping số và
  43 phương trình; VPB không có nhánh địa lý chi tiết, HDB/VIB không có nhánh
  lĩnh vực kinh doanh chi tiết.
- Hai ô VIB `Tài sản cố định — Miền Trung` là ô trống thật, không phải dấu
  `-` và không được đổi thành 0. Những trục nguồn rộng/hẹp khác schema được giữ
  source-only thay vì ép vào một leaf gần tên.
- Root 5750 `Giao dịch với các bên liên quan` có trạng thái
  `SKIPPED_BY_USER`. Nó không thuộc queue unresolved, không được scan/map và
  không được diễn giải thành bounded absence.
- Result:
  `annual2025csr8bcv1:result:8395c0524c6b1345910d057fc8bca97aba732231d7379e7c7d0eccb645f79707`.

| ID | Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | --- | ---: | --- | --- |
| ASEG-001 | ACB | 95 | Cho thuê tài chính | Schema business segment 5807–5842 chưa có trục này. |
| ASEG-002 | ACB | 95 | Chứng khoán / Quản lý quỹ | Hai trục nguồn cần phép cộng được kiểm soát trước khi đưa vào trục gộp của schema. |
| ASEG-003 | ACB | 95 | Kết quả kinh doanh bộ phận | Nhãn nguồn không xác lập rõ đây là lợi nhuận trước thuế. |
| ASEG-004 | MBB | 87 | Nước ngoài | Không đồng nhất ngữ nghĩa với trục `Khu vực khác`. |
| ASEG-005 | MBB | 83 | Thu nhập / Chi phí nội bộ | Đối trừ doanh thu/chi phí nội bộ chưa nằm trong lượt review số có giới hạn này. |
| ASEG-006 | VPB | 96 | Hoạt động công ty tài chính | Schema business segment chưa có trục riêng. |
| ASEG-007 | VPB | 96 | Hoạt động chứng khoán | Hẹp hơn trục gộp `Chứng khoán và quản lý quỹ` trong schema. |
| ASEG-008 | HDB | 61 | Nước ngoài | Không đồng nhất ngữ nghĩa với trục `Khu vực khác`. |
| ASEG-009 | HDB | 61 | Kết quả kinh doanh bộ phận | Nhãn nguồn không xác lập rõ đây là lợi nhuận trước thuế. |
| ASEG-010 | VCB | 71 | Miền Trung và Tây Nguyên | Rộng hơn trục `Miền Trung`; không được tự thu hẹp. |
| ASEG-011 | VCB | 71 | Nước ngoài | Schema địa lý hiện chưa có trục tương ứng. |
| ASEG-012 | VCB | 72 | Dịch vụ tài chính phi ngân hàng / Chứng khoán / Khác | Các trục nguồn không đồng nhất với các trục business hiện có. |
| ASEG-013 | CTG | 82 | Dịch vụ tài chính phi ngân hàng / Khác | Các trục nguồn không đồng nhất với các trục business hiện có. |
| ASEG-014 | CTG | 82 | Bảng bộ phận kinh doanh xoay | Chưa promote số theo trục khi chưa hoàn tất đối chiếu toàn hàng trên ảnh xoay. |
| ASEG-015 | BID | 37 | Cho thuê tài chính / Chứng khoán / Khác | Các trục nguồn không đồng nhất với các trục business hiện có. |
| ASEG-016 | BID | 38 | Trong nước / Nước ngoài | Không tương đương với ba trục Bắc/Trung/Nam của schema. |
| ASEG-017 | VIB | 61 | Tài sản cố định — Miền Trung | Ô nguồn nhìn thấy là trống, không phải dấu `-` hay số 0. |

## Append policy

Every later family appends entries here when a source row or complete region is
not safely mapped.  Resolved entries remain as history after an independently
replayed mapping supersedes them; the resolving result ID and commit are added
to the entry.  The following cases must be retained explicitly rather than
silently dropped:

- a visible source row with no exact schema concept;
- a plausible schema candidate whose scope is narrower, broader, or otherwise
  different from the source row;
- a VietOCR/pixel disagreement that can affect identity or numeric closure;
- a source-only parent, subtotal, optional branch, or continuation that is
  needed for graph/accounting closure but is not itself mapped;
- multiple structurally plausible regions in the same PDF;
- a whole-PDF scan with no complete region under the current contract.

For each future entry, use status `OPEN`, `NEEDS_PIXEL_REVIEW`,
`NEEDS_SCHEMA_DECISION`, `NEEDS_ACCOUNTING_RECONCILIATION`, or `RESOLVED`, in
addition to the exact machine reason.  `RESOLVED` entries remain in the file as
an audit trail and include the independent verification result ID and commit.
