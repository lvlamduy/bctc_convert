# Recurring failure-pattern registry

Updated: 2026-08-25 (UTC)

Đây là registry bắt buộc phải kiểm tra trước khi sửa shared OCR/table/mapping
logic. Chỉ ghi failure đã lặp lại, có khả năng tái diễn hoặc làm sai authority;
case riêng lẻ vẫn thuộc `UNRESOLVED_MAPPING_LEDGER.md`. Registry này không phải
mapping authority và không thay thế exact replay.

Nguồn evidence được đối chiếu khi rút gọn registry:

- `docs/experiments/OCR_MAPPING_FAILURE_PREVENTION.md` — failure và regression
  gate chi tiết;
- `CURRENT_STATUS.md` — corpus/family checkpoint và benchmark thực tế;
- `docs/experiments/UNRESOLVED_MAPPING_LEDGER.md` — case còn mở và negative
  control;
- `docs/experiments/COMPLETED_TM_FAMILIES.md` — family đã exact-replay;
- các test `accounting_*_v1`, `loan_geography_*_v1` — falsifier executable.

Trạng thái:

- `OPEN`: chưa có reusable mitigation đủ cho class đã quan sát;
- `MITIGATED`: đã có primitive/guard dùng lại được nhưng chưa chứng minh hết
  filing/layout tương lai;
- `RESOLVED`: known class đã có generic rule và regression fail-closed. Format
  hoặc family mới vẫn phải dùng lại gate, không được mặc nhiên tin input.

## RFP-001 — Vietnamese OCR noise is mistaken for semantic change

- **Failure pattern:** mất dấu, sai/thừa/mất một ký tự, dính/mất khoảng trắng,
  hoặc khác typography làm mất anchor; ngược lại fuzzy match rộng kéo nhầm một
  population khác.
- **Evidence:** `Nợ trung hạn` từng thành `Nợ trùng hạn`; `Tiền mặt` có các
  biến thể OCR như `Tiện mặt`; `chovay` mất khoảng trắng; leaf Family11 từng
  thành `? khách hạng`. Xem F-007/F-030 và các whitespace-fusion, raw-NFC,
  wrapped-scope tests của `test_accounting_scoped_table_graph_v1.py`.
- **Cause:** dùng exact raw string quá sớm, hoặc dùng một fuzzy score như
  semantic/mapping authority.
- **Anti-fix:** không thêm typo OCR làm “historical semantic alias”; không chạy
  unrestricted Levenshtein/embedding trên toàn corpus; không sửa chính tả raw
  source hay chọn schema bằng score.
- **Current primitive:** giữ raw Vietnamese NFC và accentless evidence; compiled
  exact/accentless index, bounded one-edit và đúng một whitespace-fusion channel
  chỉ tạo shortlist. Owner, population, roles, geometry, period/unit và
  accounting gates mới quyết định candidate; collision/near-neighbour thì
  unresolved. Nhãn semantic quấn dòng chỉ được ghép từ tối đa sáu source line
  liên tiếp trong cùng exact owner; bảy dòng trở lên bị chặn để không hút nhầm
  paragraph kế bên. Region-first FTS/q-gram retrieval không có mapping/absence
  authority.
- **Status:** `MITIGATED`.

## RFP-002 — Row/column/header geometry is inferred from OCR order or one bbox

- **Failure pattern:** merged/multi-tier/wrapped headers bị collapse; provider
  ordinal khác visual order; short right-aligned values tạo cột giả; row hút
  audit stamp/adjacent value; một edge/jitter pixel làm mất genuine cell/total.
- **Evidence:** CTG `Quá hạn` + `Không chịu lãi` bị OCR thành một line nhưng body
  có hai cột; VIB có adjacent rows chỉ cách 1–2 px; HDB stamp `1500`; renderer
  VPB rộng 1,623 px trong khi caller `round` ra 1,622; ACB/MBB unlabeled total
  rows cần closed, scale-derived bbox jitter. Xem F-001/F-005/F-029–033/F-045
  và geometry/total-row falsifiers trong `test_accounting_scoped_table_graph_v1.py`.
- **Cause:** coi OCR line count/order/y-overlap hoặc một tolerance tuyệt đối là
  table axis.
- **Anti-fix:** không hard-code bank/page coordinate; không globally nới bbox;
  không lấy “hai số đầu/cuối”; không để label/header text quyết định denominator.
- **Current primitive:** `adaptive_accounting_table_geometry_v1`,
  `accounting_table_axes_v1`, `accounting_family_row_axis_v1` và
  `accounting_family_column_context_v1` dựng visual bands, repeated body centres,
  spanning/deep-leaf headers và globally exclusive cells từ exact render
  dimensions. Jitter/gap/quorum là declarative closed limits với integer
  quantization; reset/next-header/first-visible-row là hard fence và raw
  bbox/source line được giữ lại. Wrapped label dùng visual-y order trong exact
  label lane thay vì provider ordinal; numeric-only observation cùng baseline
  không được làm continuation fragment. Value row phải bind đúng một physical
  baseline của wrapped label (đầu hoặc cuối), không dùng tâm của union nhiều
  dòng. Header và source-only numeric denominator của contextual child table
  được fence từ một exact structural owner chung của các additive row, không từ
  outer note parent nếu giữa hai scope còn sibling table; mixed/nonexact owner
  thì abstain. Nếu contextual subgroup nằm cùng hoặc đúng trang kế tiếp outer
  parent, chỉ header local giữa exact subgroup và valued row đầu tiên mới được
  project; continuation thường, owner không đồng nhất hoặc xa hơn một trang vẫn
  unresolved. Khi một broad parent chứa nhiều bảng sibling, body chỉ được
  project vào đúng một direct structural subgroup có ít nhất hai valued
  additive role và có exact label-only `SOURCE_ONLY_GROUP_PARENT` fence trước
  hoặc sau; thiếu/nhân đôi subgroup, valued fence hoặc không có sibling fence
  thì giữ nguyên outer region thay vì đoán. Header ngày tiếng Việt bị OCR tách dòng
  chỉ được ghép khi hai period khớp document context, fragment graph liên thông,
  có exact one-lane intersection anchor và hai nhóm typed leaf lặp lại tạo một
  partition đầy đủ; fragment rời/mơ hồ/low-confidence toàn bộ vẫn unresolved.
- **Status:** `MITIGATED`.

## RFP-003 — Continuation or repeated period blocks are joined by adjacency

- **Failure pattern:** page kế tiếp hoặc block kế tiếp có vocabulary giống nhau
  bị merge nhầm; ngược lại repeated full periods, wrapped continuation hoặc
  comparison page hợp lệ bị tách thành multiple regions.
- **Evidence:** VIB geography comparison spans adjacent pages; provision và
  securities tables có continuation; ACB/MBB có hai complete period blocks trên
  cùng page; VPB stacked transposed blocks từng cross-pair role group với scope
  của block sau.
- **Cause:** adjacency/owner text thay cho compatible topology, hoặc bắt owner/
  header phải lặp nguyên văn.
- **Anti-fix:** không merge mọi next page/block; không route bằng bank/page;
  không truncate chain khi continuation budget hết.
- **Current primitive:** `accounting_scoped_table_graph_v1` phân biệt
  same-page repeated-full, adjacent repeated-full period complement và partial
  continuation. Merge cần compatible owner/scope/roles, distinct period, unit,
  axes, ordered non-overlap, repeated/continuation evidence và không có reset.
  Budget exhaustion, conflict hoặc partial > supported proof trở thành explicit
  unresolved; original physical page IDs được giữ, zero-line pages không tạo
  reset giả. Family V4 cần full-page axis dùng public authenticated selected-page
  snapshot `1..N`; không được lấy topology cache dựng chỉ từ các line có OCR vì
  cache đó có thể biến trục `1,2,3` thành `1,3`. Regression bắt buộc gồm một
  zero-line page ở giữa và topology phải được rebuild/replay từ chính snapshot
  đầy đủ đó.
- **Status:** `MITIGATED`.

## RFP-004 — Parent, child, alternative view, or similar wording changes population

- **Failure pattern:** source-only group parent bị map/cộng lại với children;
  grand total được dùng cho strict subset; alternative table views bị cộng
  chung; wording gần nhau che mất asset/liability, gross/net hoặc broad/exact
  population.
- **Evidence:** HDB UPAS-LC/group parents; interbank asset-side `cho vay` versus
  liability-side `vay`; securities geography gross versus net; VPB/HDB/BID
  broad geography tables chứa `cho vay khách hàng` nhưng population rộng hơn;
  issuer/listing views là alternatives chứ không phải additive branches.
- **Cause:** mọi labeled/value-bearing row được xem là schema leaf, và lexical
  similarity thắng accounting scope.
- **Anti-fix:** không map cả parent lẫn children; không chọn nearest/longest
  total; không thu hẹp combined/broad source; không cộng mọi visible role set.
- **Current primitive:** declarative typed roles (`SOURCE_ONLY_GROUP_PARENT`,
  required/optional child, alternative component), owner/statement side,
  exact population/scope hard veto, complete exclusive lane axis và
  same-population equations. Shared direct-frontier closure chọn đúng một tầng
  component cho mỗi parent: child rows → subtotal, child subtotals → parent/grand
  total. Frontier không được chứa đồng thời một role và descendant đã chọn của
  role đó, không reuse occurrence/sample và phải exhaustive trên mọi lane trong
  đúng root/page/source interval. Text chỉ là anchor; unmatched source axes được
  giữ source-only hoặc unresolved.
- **Status:** `MITIGATED`.

## RFP-005 — Period or unit is inherited from an unrelated scope

- **Failure pattern:** narrative/regulatory date, packet year, nearest header
  hoặc prior/next table trở thành period; unit được kéo qua reset; duplicate
  current date hoặc relative `Số cuối kỳ/đầu kỳ` bị gán sai lane.
- **Evidence:** HDB có regulatory `31/12/2014`; MBB từng có narrative date cạnh
  table dates; BID/HDB tables có document-level million-VND/relative headers;
  Family11 có local và document-inherited period/unit lanes, kể cả full-source
  context khác sparse snapshot.
- **Cause:** nearest-text/fixed-year heuristic không bind period/unit vào owner,
  header span và value lane.
- **Anti-fix:** không dùng filename, bank, page, packet `period/year` làm PDF
  evidence; không inherit qua structural reset; không chọn first/nearest khi có
  hai candidate hoặc unit conflict.
- **Current primitive:** local exact evidence luôn ưu tiên. Nếu thiếu, typed
  PDF-internal document context yêu cầu repeated explicit consensus, exact raw
  surfaces/refs và compatibility với owner, period role, unit, axes và table
  block. Far/equidistant narrative dates, conflicting units và tampered context
  fail closed; period lane ordinal tách khỏi provider/source-column ordinal.
  One-edit parent/component authority phải rebuild column context từ original
  authenticated joined pages + evaluation policy; caller-supplied/rehashed
  period hoặc unit context không tạo authority.
- **Status:** `MITIGATED`.

## RFP-006 — Quarter, cumulative flow, balance, and roll-forward periods are conflated

- **Failure pattern:** Q2/Q3 quarter-only flow, H1/9M cumulative flow,
  point-in-time balance và opening/closing roll-forward cùng bị gắn một
  “current period” chỉ vì chung reporting end date.
- **Evidence:** annual/H1/Q1–Q4 matrix trong operating directive; các maturity,
  income/expense và roll-forward families cần period semantics khác nhau dù
  header dates trùng hoặc gần nhau.
- **Cause:** document end date được dùng như complete semantic axis.
- **Anti-fix:** không suy period kind từ filename hoặc chỉ từ một date; không
  tái sử dụng balance-axis rule cho flow/roll-forward.
- **Current primitive:** document period context và local header graph đã tách
  current/comparative/opening/closing; family spec phải khai báo balance,
  quarter-flow, cumulative-flow hoặc roll-forward semantics và replay toàn
  annual/H1/Q1–Q4 × consolidated/separate matrix.
- **Status:** `OPEN`; chưa có một shared discriminator được chứng minh cho mọi
  quarter-versus-cumulative presentation.

## RFP-007 — OCR/model disagreement is promoted to a number

- **Failure pattern:** VietOCR mất/thay digit; PP-OCR punctuation sai; Gemma
  chép số hàng xóm hoặc “sửa” số; detector box bị coi là digit authority;
  blank, visible dash và printed zero bị collapse.
- **Evidence:** VIB `97.043.85`; HDB `6.960.904/6.980.904`; CTG
  `(6.341.026)/(5.341.026)`; Gemma từng đổi `22.581` thành `22.561` và copy
  comparative `17` vào một current DASH; detector thường không sinh bbox cho
  dash. Xem F-004/F-041/F-048/F-049 và numeric reconciliation tests.
- **Cause:** confidence/model majority/equation closure được dùng để invent hoặc
  normalize source observation.
- **Anti-fix:** không backsolve digit; không coi blank là zero; không nhận raw
  dash nếu chưa pixel replay; không dùng Gemma hoặc arithmetic làm sole numeric
  authority.
- **Current primitive:** detector chỉ cung cấp geometry; semantic OCR, numeric
  reader, immutable crop và optional Gemma challenger giữ provenance riêng.
  `family_first_numeric_cell_evidence_v1` và
  `loan_geography_numeric_reconciliation_v1` giữ mọi raw candidate, typed
  `BLANK`/`DASH`/`PRINTED_ZERO`, chỉ cho equation select/veto đúng một already-
  observed assignment. Với role lặp trên cùng trang, pixel dash chỉ được bind
  khi đúng một base row của `(role, page, lane)` đang thiếu lane đó; hai row
  cùng thiếu một lane vẫn abstain, còn row cùng role đã đủ số không làm mất
  exact pixel evidence của row kế tiếp. Missing local printed control chỉ được thay bằng một
  public-replayed authenticated upstream control; không control nào được
  backsolve. Một mixed-separator cell đã có independent crop reader chỉ được
  dùng accounting corroboration khi exact coverage role của chính sample đó đi
  theo chiều component → result qua toàn bộ derived direct-frontier DAG và kết
  thúc ở một visible source total đã replay. Chuỗi chỉ-derived, nhánh rời,
  đường ngược từ parent xuống child hoặc equation không exhaustive vẫn không
  tạo numeric authority.
- **Status:** `MITIGATED`.

## RFP-008 — Content hash or cheap validation is mistaken for source authority

- **Failure pattern:** attacker/bug sửa nested field rồi self-rehash; `0 ==
  false` hoặc float/int đi qua validator; mutable snapshot/path đổi sau check;
  fabricated control/request có vẻ content-addressed nhưng không replay từ
  source.
- **Evidence:** F-021/F-025; graph, dash, request-set và customer-loan total
  regressions đều có coordinated self-rehash/source-snapshot tamper cases.
- **Cause:** closed shape/content ID chứng minh tính nhất quán nội bộ, không
  chứng minh source bytes hay execution lineage.
- **Anti-fix:** không coi self-hash/receipt JSON là authentication; không chỉ gọi
  cheap handoff validator ở public boundary; không coerce type hoặc đọc lại
  mutable path sau verification.
- **Current primitive:** exact typed JSON equality, closed field sets, lowercase
  digest/ref validation, immutable capability/snapshot bytes và public exact
  replay. Graph→overlay→numeric giữ cùng graph/cell IDs; request/control bind
  document root, full snapshot, period/unit, render/crop/source locator và được
  rebuild/replay trước khi dùng. Hardlink/extra-LF transport không được xem là
  semantically neutral. Với contextual topology V3/V4, one-edit receipt phải
  bind đúng matcher ordinal + alias ordinal + `within_role` đã chọn; matcher
  đầu tiên trong role không đại diện cho một matcher context-free/contextual
  khác.
- **Status:** `RESOLVED` cho các public contracts hiện tại; format mới phải copy
  cùng cheap-gate + authenticated-replay split.

## RFP-009 — Full-corpus replay is repeated inside each page/family operation

- **Failure pattern:** mỗi page/document/family revalidates toàn global root,
  reserializes 667,224 OCR rows hoặc rebuilds identical topology/context; một
  parser edit nhỏ dẫn tới costly full replay.
- **Evidence:** E-0046 từng mất khoảng 91 phút và hơn 200 GB logical reads;
  topology 140 docs giảm từ 137.071 s xuống 13.810 s bằng bounded workers và
  hot non-authoritative cache còn 0.075 s; family sidecar refresh 0.477 s.
  Family3 V4 cold build ngày 2026-08-24 mất khoảng 20 phút và targeted một
  filing vẫn vượt 30 giây dù hydrate snapshot chỉ dưới một giây. Profile chỉ ra
  cùng full-document snapshot/topology-candidate envelope bị build/replay lại
  theo candidate, occurrence pass và render pass. Family3 E-0178 tại clean Git
  `827d5a7` cần hai bounded build lượt vì lượt đầu đạt hard cap 300 s sau 83/140
  head-bound checkpoint; lượt resume hoàn tất 140 trial, rồi formal verify mất
  khoảng 44 s. Targeted document vẫn có ca vượt budget 30 s.
- **Cause:** safe single-item accessor đặt trong corpus loop; retrieval,
  authentication, topology và downstream projection không có same-turn handoff.
- **Anti-fix:** không bỏ replay/capability checks; không cache mutable objects;
  không chạy fuzzy/full-PDF scan trước region shortlist; không rerun full corpus
  khi impact scope chưa được chứng minh.
- **Current primitive:** authenticate one immutable batch/document snapshot,
  content-rooted per-document packets, bounded workers, same-turn typed handoff,
  small family sidecars và content/spec/engine-keyed cache (không authority).
  Region-first retrieval chỉ shortlist selected/adjacent pages và full-document
  fallback khi coverage chưa proved. Final public replay/audit vẫn giữ riêng,
  không nhân theo page/cell. Per-document checkpoint hiện giảm work bị lặp giữa
  bounded attempts và writer canonical chỉ publish pair sau đủ 140 trial, nhưng
  chưa làm cold run nằm dưới một lượt/budget.
- **Status:** `ALGORITHM_REVIEW_REQUIRED` cho Family3 V4 cho tới khi same-turn
  prepared context loại bỏ rebuild multiplicative và targeted/cold telemetry
  trở lại dưới budget; các path đã mitigated khác vẫn giữ final public replay,
  nhưng không được lặp trong inner loop.

## RFP-010 — Absence, broad scope, ambiguity, and local evidence failure are collapsed

- **Failure pattern:** không có semantic anchor, có broad/mixed population, có
  partial/ambiguous structure và malformed local evidence đều trả một trạng
  thái; một filing lỗi làm abort cả sweep.
- **Evidence:** Family11 giữ VPB/HDB/BID broad geography làm hard negatives thay
  vì narrow; Family3 pre-V4 lịch sử giữ 42 `UNRESOLVED` trong khi 84 verified và
  14 `NOT_OBSERVED_PROPOSAL_ONLY`, còn E-0178 hiện tách 126 verified / 14 bounded
  not-observed / 0 unresolved; trading sweep tiếp tục khi một document-local
  period/row gate fail.
- **Cause:** retrieval hit/miss hoặc exception được xem là mapping/absence
  decision.
- **Anti-fix:** không tuyên bố absence từ zero search hit; không đổi broad thành
  exact; không bắt một local geometry/period failure thành corpus corruption;
  không nuốt capability/schema corruption như unresolved.
- **Current primitive:** disposition tách `VERIFIED_BY_CODEX`, bounded
  `NOT_OBSERVED`, `BROAD_POPULATION_BOUNDED_ABSENCE` và `UNRESOLVED`; whole-PDF
  uniqueness và hard-veto population chạy sau retrieval. Document-local
  evidence failures được giữ theo filing; capability/root/schema corruption
  vẫn fatal.
- **Status:** `RESOLVED` cho disposition semantics; coverage của từng family vẫn
  theo `UNRESOLVED_MAPPING_LEDGER.md`.

## RFP-011 — Family graph scans the whole PDF or duplicates a private parser

- **Failure pattern:** combination/topology/geometry graph chạy trên toàn bộ
  PDF hoặc toàn selected snapshot trước khi khoanh vùng family; mỗi family lại
  copy owner window, row/column clustering, unit inheritance và bbox tolerance.
  Chi phí tăng theo mọi dòng của corpus, cùng lỗi geometry phải sửa nhiều nơi,
  và một release replay bị nhân trong từng worker/document.
- **Evidence:** Family11 sparse path từng tạo hàng trăm semantic windows và hàng
  nghìn q-gram operations chỉ trên một trang nhỏ rồi rebuild lại để replay;
  full run không hoàn tất trong development budget. Các active loan type,
  industry, maturity và quality routes vẫn có private owner/boundary/axis/row
  logic; type và industry có nhiều function cùng hình dạng. Xem RFP-002,
  RFP-005 và RFP-009.
- **Cause:** graph được dùng như retrieval engine; normalized span features
  không content-cache; shortlist không mang typed owner/child/reset evidence;
  family adapter chứa layout algorithm thay vì declarative family semantics.
- **Anti-fix:** không tăng worker để che full scan; không chạy fuzzy/full-PDF
  graph trước shortlist; không tuyên bố absence chỉ từ zero index hit; không tạo
  parser/bbox/column thresholds riêng theo bank/family; không exact-rebuild cùng
  graph trong inner loop.
- **Current primitive:** pipeline bắt buộc là immutable line/span feature index
  → family/owner/child shortlist → bounded region gồm trang trước/sau và hard
  reset/veto fence → combination 2→3 + shared geometry/topology chỉ trong vùng.
  Branchless owner+child topology là absence veto/rescue; unresolved coverage
  mới được full-document fallback. Feature/result cache dùng document content
  root + selected page set + family spec + shared-engine trust closure; cache
  không tạo authority. Exact public replay nằm tại changed-set/release boundary.
- **Status:** `OPEN`; Family12 đã dùng phần lớn shared structural primitives,
  nhưng active legacy families và Family11 runtime path chưa chứng minh đầy đủ
  region-first/cached execution.

## RFP-012 — Optional component coverage is mistaken for an exhaustive equation

- **Failure pattern:** hierarchical closure thấy đủ `minimum_component_count`
  rồi suy subtotal/parent/grand total, dù source vẫn có thể còn currency branch,
  provision, dòng `Khác`, numeric row chưa bind hoặc partial trailing total.
  Derived parent sau đó trông giống một source row hợp lệ và bị schema mapper
  phát ra.
- **Evidence:** Family3 V3 hiện khai báo các ngưỡng `1/2`, `1/2`, `1/3`, `1/3`
  và `2/3`. Falsifier chỉ có một demand-VND row và một visible loan subtotal vẫn
  có thể derive dây chuyền `DEMAND → DEPOSIT → FAMILY`; Family12 cũng đã cho
  thấy source-only/nested group không được bỏ qua chỉ vì flat subset đóng số.
- **Cause:** `minimum_component_count` chứng minh một phép cộng có thể tính,
  nhưng không chứng minh component set là exhaustive; topology `OPTIONAL` bị
  hiểu nhầm thành source absence.
- **Anti-fix:** không map derived parent từ một optional subset; không coi role
  không match là zero/absent; không bỏ unmatched numeric row, partial trailing
  row hoặc source-only group để làm phương trình đóng; không dùng accounting để
  chọn/sửa digit hay dấu.
- **Current primitive:** Family3 V4 hiện xuất và public-replay source-bound
  occurrence/hierarchy/direct-frontier receipts. Mỗi equation bind exact parent,
  ordered direct component occurrence IDs, source rows/samples, root/page/source
  interval, period/unit và toàn bộ lane. Visible/unmatched rows, optional branches,
  source-only groups, internal/trailing subtotal và presentation aliases đều phải
  được phân loại; partial/extra/duplicate/mixed-level/use-count≠1 hoặc coherent
  tamper fail closed. Accounting chỉ corroborate/veto source-observed digits và
  declared display-unit rounding; không backsolve. Family12 còn bind được một
  total in cùng dòng với exact topology parent như source-only labeled cluster:
  cluster phải là duy nhất, đủ đúng body lane/grid và trùng exact parent
  page/source-line axis; chỉ exact declared direct frontier mới được consume nó.
  Sai một digit, thiếu/nhân đôi lane, khác parent hoặc chỉ khớp rounding đều giữ
  cluster source-only và closure unresolved.
- **Status:** `MITIGATED` trên Family3 V4; primitive phải được tái chứng minh cho
  mỗi family mới, đặc biệt Family12 nested group → core subtotal → grand total.

## RFP-013 — Model page JSON is treated as reconstructed table authority

- **Failure pattern:** Gemma/full-page JSON nhìn hợp lý nhưng đổi digit, bỏ hoặc
  gộp column, invent header/row, hay gán cell sang period/population khác; output
  sau đó được dùng trực tiếp để map thay vì làm challenger.
- **Evidence:** Gemma từng đổi `22.581` thành `22.561`, copy comparative `17`
  vào current DASH, và full-page transcription cần context để giữ multi-level
  header. F-004/F-010/F-011/F-011A đã chứng minh prompt dài, crop quá sớm và
  JSON-looking output đều không tạo numeric/geometry authority.
- **Cause:** closed JSON hoặc model agreement bị xem là source replay; prompt
  trộn transcription, arithmetic và schema decision; response không bind đầy đủ
  page pixels, model/settings, prompt và raw output.
- **Anti-fix:** không đưa ReportNormId/expected value vào prompt; không để Gemma
  một mình quyết định row, column, digit hay mapping; không chạy full-page trên
  mọi trang; không resize/crop mất header context trước structure rescue.
- **Current primitive:** existing hosted Gemma artifacts bind selected page/crop
  hashes and keep numeric disagreement non-authoritative, nhưng chưa có shared
  schema-blind page-structure challenger contract. Contract chung phải giữ exact
  page/crop ref, prompt/model/settings/raw response/closed JSON, rồi đối chiếu
  native text, PP-OCR geometry, VietOCR, row/column topology và accounting. Chỉ
  trigger khi primary unresolved hoặc layout mới; disagreement giữ unresolved.
- **Status:** `OPEN`.

## Pre-change gate

Trước một generic fix mới:

1. tìm pattern gần nhất ở registry này và đọc evidence ledger được dẫn;
2. thêm falsifier cho anti-fix đã từng thất bại, không chỉ positive fixture;
3. sửa shared primitive/spec, không route bằng bank/file/page/note/year;
4. giữ raw Vietnamese, bbox, source line, period/unit và numeric provenance;
5. chạy focused replay trước, targeted impacted documents sau; chỉ chạy full
   corpus khi impact/authority gate thực sự yêu cầu;
6. cập nhật status ở đây chỉ khi reusable primitive và regression đã tồn tại.

## Repeat/runtime circuit breaker

Một `failure signature` gồm shared stage/primitive, failure class, reason code và
implementation/spec revision; bank, page, filing ordinal và expected value không
được đưa vào signature để che một lỗi generic thành nhiều case riêng.

- Lần đầu: giữ raw evidence, thêm matched falsifier và chỉ chạy targeted impacted
  documents.
- Cùng signature thất bại lần thứ hai dưới cùng revision: đặt
  `ALGORITHM_REVIEW_REQUIRED`; cấm chạy lại full-corpus sweep. Phải so lại giả
  định topology/geometry, profile stage và benchmark ít nhất một phương án
  primitive hoặc OCR/model challenger phù hợp.
- Cùng signature thất bại lần thứ ba: không được tiếp tục nới threshold/bbox hay
  thêm alias. Phải thay revision thuật toán/OCR hoặc để case `UNRESOLVED` với
  evidence rõ ràng.
- Runtime budget phải được khai báo trước command. Một stage vượt budget hai lần
  dưới cùng revision cũng trở thành `ALGORITHM_REVIEW_REQUIRED`; tối ưu bằng
  region-first, per-document content roots, incremental DAG hoặc batch snapshot,
  không bỏ authority gate.
- Default development budgets cho family-first là: focused unit/contract panel
  dưới 10 giây; targeted impacted-document panel dưới 30 giây; cold 140-filing
  family build mục tiêu dưới 180 giây và hard stop ở 300 giây. Warm unchanged
  run phải chủ yếu là verified cache hits. Family có OCR/model rescue phải khai
  báo riêng số crop và per-crop budget, nhưng deterministic graph/release stage
  vẫn không được vượt hard stop bằng cách giấu model time vào subprocess.
- Mọi benchmark phải báo ít nhất source lines/pages, candidate lines/pages,
  semantic-window count, cache hit/miss, cold/warm elapsed và peak worker count.
  Dữ liệu lớn chạy bằng content-addressed incremental shards; không được dùng
  extrapolation của full sequential scan làm production plan.
- Chỉ mở lại full sweep sau khi revision/spec thực sự đổi (hoặc source drift độc
  lập được chứng minh), focused + adversarial + targeted panels đều xanh, và
  telemetry cho thấy stage nằm trong budget. Full build/verify là release gate,
  không phải vòng debug.
