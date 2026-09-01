# Recurring failure-pattern registry

Updated: 2026-08-26 (UTC)

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
  unresolved. Region-first FTS/q-gram retrieval không có mapping/absence
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
  bbox/source line được giữ lại.
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
  same-population equations. Text chỉ là anchor; unmatched source axes được giữ
  source-only hoặc unresolved.
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
  observed assignment. Missing local printed control chỉ được thay bằng một
  public-replayed authenticated upstream control; không control nào được
  backsolve.
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
  semantically neutral.
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
  theo candidate, occurrence pass và render pass.
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
  không nhân theo page/cell.
- **Status:** `ALGORITHM_REVIEW_REQUIRED` cho Family3 V4 cho tới khi same-turn
  prepared context loại bỏ rebuild multiplicative và targeted/cold telemetry
  trở lại dưới budget; các path đã mitigated khác vẫn giữ final public replay,
  nhưng không được lặp trong inner loop.

## RFP-010 — Absence, broad scope, ambiguity, and local evidence failure are collapsed

- **Failure pattern:** không có semantic anchor, có broad/mixed population, có
  partial/ambiguous structure và malformed local evidence đều trả một trạng
  thái; một filing lỗi làm abort cả sweep.
- **Evidence:** Family11 giữ VPB/HDB/BID broad geography làm hard negatives thay
  vì narrow; interbank sweep giữ 42 `UNRESOLVED` trong khi 84 verified và 14
  `NOT_OBSERVED_PROPOSAL_ONLY`; trading sweep tiếp tục khi một document-local
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
- **Current primitive:** hierarchical closure giữ visible/derived provenance và
  dùng mismatch làm veto, nhưng chưa xuất một source-bound visible-coverage
  receipt chứng minh toàn bộ body numeric axis đã bind và mọi equation dùng đúng
  exhaustive population. Trước khi mapping derived parent cần shared coverage
  gate: bound/unmatched rows, source-only groups, optional visible branches,
  unique complete trailing total và exact component-policy receipt.
- **Status:** `OPEN`.

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
- **Historical primitive:** các hosted Gemma artifact cũ bind selected page/crop
  hashes và chỉ dùng model làm challenger đối chiếu native text/PP-OCR/VietOCR/
  geometry. Đây là ranh giới của pipeline OCR lịch sử, không còn là kiến trúc
  đọc của pipeline Gemini JSON-first.
- **Current JSON-first boundary:** Gemini là reader duy nhất nhưng PDF/ảnh trang
  bất biến vẫn là source cuối cùng; raw response, prompt/schema/model/provider,
  image hash/DPI và token/cost phải được giữ. JSON có thể tạo table/hierarchy
  candidate nhưng không tự tạo schema-mapping authority. Digit/hierarchy phải
  qua strict contract, repeat/hard-page audit và exhaustive direct-frontier
  equations; bất đồng không được sửa bằng PP-OCR/VietOCR/geometry fallback.
- **Status:** `OPEN`.

## RFP-014 — Derivable bookkeeping and deep cross-field constraints destabilize model JSON

- **Failure pattern:** structured output trả đúng hình dạng tổng quát nhưng sai
  ID/source-order kỹ thuật, tự đặt tên cho subtotal không nhãn, hoặc tạo thêm cột
  nhãn dù vector chỉ có các cột giá trị. Deep provider schema cũng có thể trả
  HTTP 500/capacity error trước khi sinh token.
- **Evidence:** pilot Gemini 3.7 Flash ngày 2026-08-26 trên cùng MBB trang 31:
  lần đầu sinh `section_1` và source order bắt đầu từ 1; sau khi bỏ ID, một lượt
  tự đặt `Tổng cộng` trong hierarchy của hàng không nhãn; lượt khác thêm column
  `TEXT` có header `null`. Hai direct-Google Flex attempt với schema sâu trả
  HTTP 500 và không có usage; một OpenRouter Vertex Flex attempt trả
  `finish_reason=error`, 0 token/0 cost. Strict validator đã chặn tất cả.
  Trên MBB trang LCTT 7 ở 300 DPI, receipt đặt trước `sections` chỉ đếm 26/33
  hàng và 1/2 bảng. Sau khi ép receipt xuống cuối, section/table/row/cell khớp
  1/1/33/99 nhưng model vẫn tự đếm populated-cell sai 61 thay vì 63. Output thật
  chỉ dùng khoảng 3,6K/65,5K token và kết thúc `stop`, nên đây là lỗi self-count,
  không phải token truncation.
  MBB trang CĐKT 3 lặp hai lần đều trả literal `" -"` cho hai dash dù prompt đã
  cấm rõ whitespace; cùng trang chép đúng 39 hàng/117 cell và 11/11 phương trình
  nhiều tầng, nhưng gán một số subtotal thành `ITEM` dù hierarchy đúng.
- **Cause:** bắt model sinh dữ liệu có thể suy ra từ array position; kỳ vọng JSON
  Schema biểu diễn được cross-field equality/array-width/visible-label truth;
  prompt quá ngắn không nói rõ cột nhãn và unlabeled subtotal.
- **Anti-fix:** không normalize `section_1→s1`, renumber hoặc chèn/bỏ cột sau
  response; không biến invented label thành source; không retry billed semantic
  failure; không hạ DPI để giảm token trên scan mờ.
- **Current primitive:** model contract chỉ chứa source content; ID/order được
  derive trong database projection. Prompt/schema nói rõ columns chỉ là value
  columns và unlabeled row kết thúc path bằng `null`; request pin seed 0. Raw
  response được lưu trước validation. Chỉ retry cùng model/provider cho HTTP
  retryable hoặc zero-token/zero-cost provider error. Ảnh chỉ dùng 200/300 DPI.
  Local validator giữ closed fields, exact row width/path invariant; accounting
  equations kiểm tra multi-level subtotal sau transcription. Completion receipt
  nằm sau sections và chỉ giữ các count cấu trúc code có thể replay exact;
  populated-cell được code tự tính, không lấy self-count model làm authority.
  Raw whitespace-wrapped dash và `_` biệt lập được giữ nguyên và chỉ projection
  dẫn xuất mới phân loại `DASH`; chuỗi chứa `_` cùng ký tự khác vẫn là `VALUE`.
  Whitespace quanh chữ/số vẫn reject. `row_kind` là proposal,
  subtotal/total phải được graph + exact direct-frontier equation tái xác nhận.
- **Status:** `MITIGATED` trên hard-page pilot; chưa `RESOLVED` trước whole-PDF
  và cross-page/repeat panel.

## RFP-015 — Text Batch success does not prove multimodal Batch capability

- **Failure pattern:** một provider/model xử lý text Batch bình thường nhưng từ
  chối ảnh ở giai đoạn Batch validation/serialization; hoặc Files API image chạy
  đúng ở `generateContent` thường nhưng thất bại khi đặt trực tiếp trong inline
  Batch. Nếu chỉ probe text rồi mở full corpus, toàn bộ job ảnh có thể thất bại
  dù model và credential vẫn khỏe.
- **Evidence:** ngày 2026-08-26, OpenRouter Batch `google/gemini-3.7-flash`
  hoàn tất text JSON 61 token, nhưng image data-URI bị cấm; cùng ảnh qua URL S3
  HTTPS ký hợp lệ vượt input validator rồi Vertex adapter trả lỗi typed rằng
  serializer Batch không hỗ trợ image. Google direct inline Batch nhận ảnh
  base64 và Files URI nhưng per-request đều `INVALID_ARGUMENT`; Files URI đó
  chạy thành công qua `models/gemini-3.7-flash:generateContent` với 1.754 input
  và 4.132 output token. Tài liệu Google chỉ dẫn multimodal Batch lớn qua file
  JSONL tham chiếu các File API resources.
  Probe bổ sung cùng ngày đặt hai ảnh 300 DPI/base64 trong hai request của một
  batch 3.404.103 byte: submission được nhận nhưng terminal 2/2 failed,
  `usage=null`, với cùng typed rejection đối với base64/data-URI; đây không phải
  giới hạn do chỉ có một ảnh hoặc do kích thước request quá nhỏ.
- **Cause:** capability khác nhau theo transport endpoint và adapter; text,
  synchronous multimodal, inline Batch và JSONL file Batch không tương đương.
  Tài liệu OpenRouter Batch Beta ngày 2026-08-26 xác nhận transport hiện
  `text-only` và reject cả image URL lẫn `input_image`/`input_file`; trong khi
  catalog của chính model Batch vẫn liệt kê image/PDF/audio. Catalog capability
  không phải endpoint capability. OpenRouter Files API cũng không công bố
  `file_id` binding cho Batch, nên upload file hoặc S3 presigned URL không thể
  tự tạo ra một media transport chưa được adapter hỗ trợ.
- **Anti-fix:** không suy image Batch từ model catalog/text Batch; không retry
  cùng wire shape khi đã có typed unsupported/invalid-argument; không nhét URL
  có credential vào DB/log; không chuyển semantic failure thành provider
  fallback.
- **Current primitive:** trước corpus phải có một actual image request thành
  công trên đúng endpoint/wire shape. Google multimodal dùng Files API + JSONL
  Batch; OpenRouter dùng Vertex Flex đồng bộ cho tới khi một image Batch
  capability probe thật sự qua. Batch/job/page IDs được lưu resumable; ảnh S3
  là object content-addressed bất biến, receipt chỉ giữ URL hash/expiry chứ
  không giữ presigned URL.
- **Status:** `MITIGATED`; Google JSONL image Batch positive đã hoàn tất 1/1,
  còn whole-PDF/two-key/resume gate trước corpus.

## RFP-016 — Credential existence does not prove Batch or capacity capability

- **Failure pattern:** một API key gọi được metadata/upload hoặc từng endpoint
  khác nhưng không đủ billing/tier/capacity cho Batch; nếu round-robin mù trên
  corpus, một nửa job có thể kẹt hoặc thất bại trước inference.
- **Evidence:** ngày 2026-08-26, Google slot sinh viên upload đủ 30 ảnh và JSONL
  nhưng create Batch trả HTTP 400 `FAILED_PRECONDITION`. Một direct-standard
  request đúng model/ảnh/prompt trên cùng slot chờ 849,178 giây rồi HTTP 503
  `CAPACITY_SHED`, `usage=null`. Slot trả phí `…UrJOHw` nhận hai Google JSONL
  Batch 30+30 trang và chuyển sang `BATCH_STATE_RUNNING`.
- **Cause:** capability và quota/billing được xét theo credential + endpoint +
  tier, không thể suy từ việc key có cú pháp hợp lệ hay upload file thành công.
- **Anti-fix:** không retry vô hạn; không chia việc round-robin trước capability
  gate; không chuyển lỗi precondition/capacity thành kết quả OCR rỗng.
- **Current primitive:** mỗi credential có typed capability receipt. Chỉ slot đã
  hoàn tất một image Batch positive mới nhận corpus jobs; slot lỗi được giữ lại
  để probe lại có kiểm soát khi quota/billing thay đổi.
- **Status:** `OPEN`; slot trả phí đang chạy whole-PDF gate, slot sinh viên chưa
  có Batch positive.

## RFP-017 — Page validator becomes a second layout parser

- **Failure pattern:** OCR JSON contains every visible label and value, but the
  page is rejected because the model chose `GROUP` instead of `SUBTOTAL`, placed
  a visible title in `table.title_exact` instead of `narratives_exact`, or used a
  different but coherent hierarchy path.
- **Evidence:** MBB Q1/2025 p3 and p31 under the balanced and simple prompts have
  identical row/cell/populated-cell coverage (39/117/94 and 21/84/80) and exact
  financial values. Only soft placement/classification differs. Rejecting either
  representation would discard good OCR before the graph layer can evaluate it.
  Whole-PDF simple-prompt replay exposed the same defect more directly: 9 pages
  had complete JSON and normal `STOP`, but 8 encoded the printed label column in
  `columns` while keeping that cell in `label_exact`, and one omitted only a
  decorative leading hyphen from the final hierarchy item. All 9 raw responses
  replay after generic canonicalization, including p32 with 24 rows/96 cells.
  Corpus production exposed two further complete representations in ACB H1/2025:
  p76 packed adjacent money cells with a literal `凸` sentinel, and expanding
  only deficient rows yielded exactly 24 rows × 9 declared columns; p83 used
  leading `null` only for blank levels of a merged column header and `-凸-` for
  a same-cell accounting dash, while retaining 22 rows × 8 declared columns.
  Both replayed from already billed raw responses and matched the page images;
  no third provider call was needed.
- **Cause:** mixing transport/schema integrity with accounting interpretation.
- **Anti-fix:** do not encode every observed bank/page layout in JSON validation;
  do not require LLM `row_kind` or hierarchy to be mapping authority; do not
  retry a complete page merely to force one preferred serialization.
- **Current primitive:** hard validation is limited to parseable bounded JSON,
  required fields/types, status/data consistency and true value-width
  consistency. If every row omits exactly one leading textual column because
  that cell is already held in `label_exact`, the canonical projection removes
  that redundant column while the immutable provider response is retained.
  A packed-cell sentinel is expanded only when the row is deficient, every
  segment is nonblank and the ordered expansion closes the declared width
  exactly. Blank levels in merged column headers are omitted from the canonical
  path; a same-cell pack consisting solely of dash glyphs projects to one dash.
  Title placement, row kind and hierarchy are proposals consumed by indexed
  retrieval, graph variants and exact accounting equations later.
- **Status:** `MITIGATED`; simple-prompt p3/p13/p31 pilots pass. Keep adding
  layout fixtures, but expand soft graph normalization rather than hard page
  rejection unless source data itself is missing or structurally unusable.

## RFP-019 — Billed semantic response is retried instead of replayed

- **Failure pattern:** provider returns a normal billed JSON response, page
  validation rejects one soft convention, then document-level retry calls the
  provider again even though the immutable raw response could be revalidated
  after a canonicalizer fix.
- **Evidence:** the first 89-page OpenRouter production document ingested 86
  pages. Page 44 had a genuine zero-usage provider error and succeeded on retry.
  Pages 76/83 each returned complete billed output twice but failed the old
  structural validator both times. Offline replay under commit `42c5a12`
  recovered 24×9 and 22×8 cells in 19.5 seconds, reused 87 cached pages, made
  zero provider requests and closed manifest
  `gfdmv1:manifest:606439b26e01eccbda991efb4f032984bd6feeafea44e1e884d6fbbc10a49a6e`.
- **Cause:** semantic validation failure and retryable transport/provider failure
  shared the same document `NEEDS_RETRY` state; failure artifacts also omitted
  the exception message.
- **Anti-fix:** do not blindly resubmit billed semantic output; do not overwrite
  the old raw response or erase the failed task history; do not mark a partial
  document successful before every physical page has one extraction.
- **Current primitive:** the runner checks cache, then replays every immutable
  semantic raw response before authorizing a provider call. A still-invalid
  semantic page is non-retryable and records the exact exception message.
  `--offline-replay-only` makes recovery impossible to route to a provider, and
  a dedicated append-only `FAILED→SUCCEEDED` receipt is allowed only after the
  full document manifest closes with no semantic/offline-missing page.
- **Status:** `MITIGATED`; actual 89-page recovery passed. Final cost reporting
  must include the two historical duplicate billed semantic attempts rather
  than relying only on successfully ingested extraction runs.

## RFP-018 — Provider batch success is not page extraction success

- **Failure pattern:** Google marks a Batch request successful at the operation
  layer although the model candidate ends with `RECITATION` and contains no JSON;
  retrying the same page repeatedly cannot complete a document manifest.
- **Evidence:** MBB Q1/2025 simple-prompt Batch completed 30/30 transport requests
  in both chunks. Page 13 nevertheless returned `RECITATION` with 1.304 input and
  zero output token, then repeated the same typed failure in a dedicated Batch.
  The same 300-DPI page completed through OpenRouter Vertex Flex in one call with
  2.592 input/1.266 output tokens and exact financial narratives.
- **Cause:** operation-level `successfulRequestCount` means the request reached a
  model response, not that a normal complete JSON candidate exists.
- **Anti-fix:** do not count Batch statistics as ingested pages; do not retry an
  identical typed failure indefinitely; do not replace a failed page with empty
  content or mix two provider outputs without page-level provenance.
- **Current primitive:** each provider result passes its own finish/JSON/page gate.
  After the bounded Google retry budget, only exact failed physical pages move to
  OpenRouter Flex. The document manifest records the gateway and service tier per
  page and requires exactly one allowed extraction for every page; duplicate
  eligible extractions make the manifest ambiguous and fail closed.
- **Status:** `MITIGATED`; 60-page mixed-provider manifest and isolated automated
  fallback supervisor gate are the release evidence, not the provider Batch count.

## RFP-020 — Prose transcription triggers recitation and wastes output budget

- **Failure pattern:** prompt yêu cầu chép toàn bộ prose của thuyết minh dù tầng
  family chỉ cần statement/table/line-item. Response dài giống tài liệu công
  khai có thể bị provider kết thúc bằng `RECITATION`; trang prose-only cũng tiêu
  nhiều output token mà không thêm dữ liệu mapping.
- **Evidence:** sáu hard pages chạy prompt `items` đã đóng với tổng
  `0.012789 USD`: prose-only trả JSON tối thiểu, còn bảng/khoản mục giữ label và
  value. ACB H1/2025 hợp nhất p22 chứng minh giới hạn còn lại: bảng tài sản bảo
  đảm 12 hàng đọc đúng khi crop bounded, nhưng cụm 5 nhãn nhóm nợ vẫn bị Google
  `RECITATION`; OpenRouter Vertex image Batch không hỗ trợ cả data-URI lẫn URL
  S3 ký.
- **Cause:** scope transcription rộng hơn dữ liệu cần index; provider similarity
  filter áp dụng độc lập trên mỗi response. Đây không phải chat context leakage:
  request không gửi history hoặc `cachedContent`.
- **Anti-fix:** không biến `RECITATION` thành trang rỗng; không retry vô hạn cùng
  prompt/ảnh/provider; không gắn output prompt `items` vào cache key `simple`;
  không né safety bằng encoding; không quay về PP-OCR/VietOCR/geometry.
- **Current primitive:** prompt `items` có version/hash riêng, chỉ nhận primary
  statements, bảng và line-item lists; prose-only trả
  `NO_RELEVANT_FINANCIAL_CONTENT`. Raw response và finish reason được giữ; trang
  `simple` hợp lệ được projection bằng code, còn trang thiếu source content đi
  qua bounded provider/tile fallback với receipt source/page/coverage riêng.
- **Status:** `MITIGATED`; GJF-OPEN-001 đã đóng bằng current document-manifest
  selection trên ảnh nguyên trang. Corpus supervisor hiện phân loại độc lập
  `RECITATION → scope`, semantic/JSON → `items`, giữ prompt hash riêng và chỉ
  đóng task khi current page frontier phát lại đầy đủ. Full-corpus freeze vẫn là
  release gate cuối, không phải điều kiện để giữ case này OPEN.

## RFP-021 — Upload ảnh Batch bị ngắt bị nhầm là batch đã submit

- **Failure pattern:** process bị ngắt sau khi upload một phần ảnh lên Google
  Files API nhưng trước khi tạo JSONL, manifest và submission response. Lần chạy
  tiếp thấy artifact directory không rỗng rồi dừng vĩnh viễn; nếu xóa mù hoặc
  submit lại sau một response bị mất thì có thể mất forensic evidence hoặc tạo
  batch trùng.
- **Evidence:** hai attempt production bị ngắt ở ranh giới pre-submission giữ
  lần lượt 17 và 10 receipt ảnh, không có `batch-input.json`, manifest,
  submission response hoặc batch ID. Chúng được dời nguyên vẹn sang
  `abandoned-google-attempts`; attempt sạch sau đó tiếp tục từ ledger mà không
  submit trùng.
- **Cause:** resumability trước đây chỉ hiểu hai trạng thái directory rỗng hoặc
  có `submission-receipt.json`, chưa mô hình hóa upload frontier dở.
- **Anti-fix:** không `rm` receipt upload; không coi directory không rỗng là bằng
  chứng batch đã submit; không tự resubmit nếu đã có JSONL/manifest/submission
  response nhưng thiếu receipt, vì authority boundary khi đó không còn đủ.
- **Current primitive:** chỉ quarantine tự động khi top-level chứa đúng một
  `uploaded-files/`, mọi file là single-link JSON receipt của một image và chưa
  có `batch-input.json`. Quarantine có content ID, SHA/size từng receipt và là
  thao tác move có thể phục hồi. Bất kỳ shape muộn hơn vẫn fail-closed để audit
  provider trước khi tiếp tục.
- **Status:** `MITIGATED`; focused positive/unsafe-boundary falsifier và corpus
  resume thực tế đã qua.

## RFP-022 — Prompt ngắn bỏ placeholder của ô trống trong bảng nhiều cột

- **Failure pattern:** model nhận đúng số cột và chép đúng các số nhìn thấy,
  nhưng với hàng có một hoặc nhiều ô trống nó chỉ trả các ô có giá trị. Vector
  `values_exact` vì vậy ngắn hơn `columns` và không còn cách xác định chắc chắn
  số thuộc cột nào nếu chỉ nhìn JSON.
- **Evidence:** VCB quý 3/2025 công ty mẹ, trang vật lý 40, ảnh nguyên trang
  300-DPI SHA `01c6e5fd...`: cả prompt `simple` và `items` đều trả 5 cột nhưng
  một số subtotal chỉ có 4, 2 hoặc 1 phần tử, cùng lỗi
  `row values do not align with table value columns`. Một retry `balanced` trên
  đúng ảnh buộc giữ `null` ở ô trống, qua validation và đóng manifest 52 trang
  `gfdmv1:manifest:f79ea864...` với 505 hàng/1.807 ô; không OCR lại 51 trang đã
  hợp lệ. VCB quý 1/2026 hợp nhất p34 lặp lại cùng signature trên bảng biến động
  vốn 11 cột: `simple`/`items` cho hàng 10 hoặc 9 phần tử, còn `balanced` trả
  7/7 hàng đúng 11 vị trí, page JSON SHA `d557be04...`, rồi đóng manifest 53
  trang `gfdmv1:manifest:d0d157d6...` mà không OCR lại 52 trang tốt.
- **Cause:** prompt ngắn nhấn mạnh chép đủ giá trị nhìn thấy nhưng chưa nói rõ ô
  trống vẫn chiếm một vị trí trong vector ngang; JSON Schema chỉ kiểm tra kiểu,
  không biểu diễn được ràng buộc độ dài bằng số cột của cùng table.
- **Anti-fix:** không tự chèn `null` theo phỏng đoán, không nới validator cho
  vector lệch cột, không dùng geometry/OCR cũ để gán số vào cột và không chạy lại
  toàn tài liệu.
- **Current primitive:** semantic failure trước hết dùng prompt `items`; chỉ khi
  retry đó vẫn là semantic failure mới dùng một retry `balanced` có hash/version
  riêng trên đúng page-image SHA. Prompt cuối yêu cầu `values_exact` bằng đúng số
  cột, dùng `null` cho ô thật sự trống và chuẩn hóa mọi ô chỉ có dấu gạch thành
  chuỗi `"0"`, nên glyph dấu gạch không thể dính vào số lân cận. Nếu provider
  retry ngắn chuyển thành semantic failure, scheduler tiếp tục đúng chuỗi
  `simple → items → balanced` thay vì dừng sớm. Manifest hiện hành bind prompt
  riêng theo trang; cơ chế resume kiểm tra lại toàn bộ image frontier rồi niêm
  phong ledger mà không gọi provider lại.
- **Status:** `MITIGATED`; actual recovery VCB 52/53 trang và MBB Q4 hợp nhất
  61 trang (GJF-CLOSED-016), stale-image/cascade falsifiers và 175 test Gemini
  JSON-first đã qua.

## RFP-023 — Google Files upload-start 429 làm chết toàn corpus supervisor

- **Failure pattern:** một Files API upload-start trả HTTP 429 trước khi tạo
  upload session; batch subprocess thoát 1 nhưng supervisor coi đây là lỗi ngoài
  disposition, hủy các submit future khác và dừng toàn corpus.
- **Evidence:** task HDB quý 2/2025 công ty mẹ p1–30
  `gjfptaskv1:1f6dd08d...` lặp đúng hai lần. Cả hai lần attempt directory rỗng,
  không có upload receipt, JSONL, manifest, submission response hoặc batch ID;
  direct diagnostic xác nhận exception chính xác
  `Google file upload start returned HTTP 429`.
- **Cause:** uploader có typed exception nhưng subprocess boundary làm mất kiểu;
  scheduler chỉ chấp nhận exit 0 và không có cooldown cho pre-submission rate
  limiting.
- **Anti-fix:** không đánh dấu task `FAILED`, không tăng attempt ledger khi chưa
  submit, không xóa/quarantine evidence sau ranh giới JSONL/manifest, không
  restart supervisor liên tục và không đoán rằng HTTP 429 đã tạo batch.
- **Current primitive:** subprocess error giữ return code/stdout/stderr nội bộ;
  chỉ upload-start 429/5xx/timeout trước ranh giới submission được đổi thành
  `RETRYABLE_GOOGLE_UPLOAD_START`. Supervisor ghi receipt content-addressed,
  giữ task ở trạng thái cũ, giới hạn đúng một Google uploader và dùng cooldown
  toàn cục 30 giây để các task không đồng loạt thử lại. Nếu đã có JSONL,
  manifest hoặc submission evidence thì vẫn fail-closed; partial image-upload
  frontier chỉ được xử lý bởi quarantine receipt của RFP-021.
- **Status:** `OPEN`; commit `c91a997fc8472ea182b593ec20c952353a73f8db`,
  181 test Gemini JSON-first và actual deferral receipt đã qua. Cần một actual
  retry sau deferral tạo batch ID mà không trùng trước khi chuyển `MITIGATED`.

## RFP-024 — PDF CropBox/MediaBox cắt mất nội dung scan trước khi gửi Gemini

- **Failure pattern:** ảnh nhìn như nguyên trang theo renderer mặc định nhưng
  thực tế chỉ là phần giao với `CropBox/MediaBox`; bảng bị mất cột hoặc góc dù
  model và prompt đều đúng.
- **Evidence:** ACB kiểm toán năm 2025 công ty mẹ p57 xoay 270°. Page box chỉ
  595,68×842,40 pt nhưng scan source vẽ từ x=-124,277 tới x=719,957 pt. Ảnh cũ
  3.510×2.482 px SHA `97aa43fa...` làm cả `simple` và `items` trả
  `UNRESOLVED_PAGE` vì mất cột bên phải. Ảnh whole-page 3.510×3.535 px SHA
  `ea85078c...` giữ toàn painted source và trả đủ bảng 7 cột, 13 hàng/91 ô.
- **Cause:** PDF page-box metadata không bao hết image XObject đã được đặt lên
  trang; rasterizer chuẩn tôn trọng box nên cắt pixel trước khi model nhận ảnh.
- **Anti-fix:** không crop theo bảng/geometry, không nới semantic validator để
  chấp nhận bảng thiếu cột, không ghép JSON từ ảnh cũ với ảnh mới và không suy
  đoán phần đã bị cắt. Phần con dấu vốn chỉ là một strip ảnh rời trong PDF cũng
  không được “vẽ bù”.
- **Current primitive:** renderer đọc toàn `MediaBox`, kiểm tra display-list
  painted bounds và chỉ mở rộng canvas vật lý trong giới hạn niêm phong; receipt
  bind source SHA, box gốc/chọn, DPI, kích thước và image SHA. Current document
  manifest chỉ nhận đúng page version mang image SHA whole-page; cache ảnh cũ
  trở thành stale và phải reprocess.
- **Status:** `MITIGATED`; GJF-CLOSED-014/GJF-CLOSED-017 và cuộc kiểm tra repair
  toàn corpus đã xác định 644 trang thuộc 21 tài liệu cần whole-page handling.
  Trong 636 trang đã OCR, render lại trực tiếp từ PDF ở 300 DPI khớp tuyệt đối
  SHA/kích thước với page-version trong database (`636/636`, mismatch `0`);
  tám trang chưa OCR sẽ dùng primitive mới ngay từ request đầu. Không còn
  `REPAIR_REQUIRED` trong status frontier đã kiểm tra.

## RFP-025 — Validator ép Gemini chép lại ngoài scope và làm mất mapping đúng

- **Failure pattern:** crop/table response đã đọc đúng toàn bộ ô cần sửa và mọi
  phương trình đều đóng, nhưng validator loại response vì model đổi newline ở
  header, gộp unit vào header, trim khoảng trắng quanh dash hoặc biểu diễn khác
  một ô ngoài allowlist. Scheduler sau đó đổi thinking/prompt và trả tiền nhiều
  lần cho cùng một evidence đúng; tệ hơn, terminal có thể ghi `COMPLETE` khi vẫn
  còn job `ABSTAINED`.
- **Evidence:** Family 13 table-repair ngày 2026-08-27 tạo 14 attempt. Trong 12
  response có bảng, cả 12 đều đúng target/collateral và equation; sáu crop đều
  khớp trực quan. Chỉ cần 7 attempt sớm nhất để đóng đủ 6 job. Validator cũ chỉ
  nhận 3 job vì so byte toàn bảng; run cũ ghi sai `COMPLETE` với
  `RESOLVED=3, ABSTAINED=3` và tạo partial overlay, hiện đã quarantine.
- **Cause:** prompt bắt model vừa OCR vừa tái tạo schema/trạng thái/context và
  echo mọi ô byte-exact; validator trở thành layout serializer thay vì chiếu
  observation lên source graph bất biến. Retry thay prompt được dùng thay cho
  việc sửa canonicalizer/mapper.
- **Anti-fix:** không thêm điều kiện/prompt riêng theo bank/file/page; không bắt
  Gemini sinh graph, ReportNormId, phương trình hoặc lặp lại ô ngoài scope;
  không retry billed response chỉ để đổi serialization; không publish nếu bất
  kỳ planned job nào chưa `RESOLVED`.
- **Required primitive:** một schema nhỏ cố định
  `{observations:[{cell_id,source_text}]}`. Code canonicalize cell ref, dash,
  blank, printed zero, số âm/dấu phân cách; identical duplicates corroborate,
  conflicting target duplicates fail. Observation ngoài allowlist bị bỏ qua và
  lưu diagnostic; immutable base page cung cấp mọi ô còn lại. Chỉ thiếu/xung đột
  target hoặc structure thật sự thiếu mới tự động chuyển theo tập prompt bounded
  đã khai báo (`simple → items → balanced/context`). Graph, unit, period và
  equation được code kiểm sau projection, không backsolve trong prompt.
- **Release gate:** ưu tiên offline reproject raw response đã niêm phong và không
  gọi provider lại. Chỉ `RESOLVED == planned_job_count` và `ABSTAINED == 0` mới
  tạo overlay/frontier, publish cả DB pair và ghi terminal `COMPLETE`; mọi trạng
  thái khác giữ DB đích nguyên byte và ghi `INCOMPLETE`.
- **Status:** `CLOSED` ngày 2026-08-28. Primitive hiện dùng đúng schema tối giản
  `{observations:[{cell_id,source_text}]}`; 12/12 response bảng đã niêm phong
  được reproject, sáu job đóng `RESOLVED=6/ABSTAINED=0` với
  `provider_call_count=0`. Thuật toán tự canonicalize representation drift,
  giữ nguyên base ngoài target, kiểm graph/equation cục bộ và chỉ publish khi
  đủ toàn bộ job. Family 13 đã OFFICIAL `R140/N0/U0/M1281`; Family 14 dùng
  source-replay cùng nguyên tắc và đã OFFICIAL `R64/N76/U0/M254`. Runtime chỉ
  tạo một work database cho mỗi database-role cần publish (page/results) và tối
  đa một immutable source view trong suốt lần chạy, rồi xóa sau atomic publish;
  tuyệt đối không tạo snapshot theo attempt, job hoặc prompt. Các database
  nguồn/effective/production content-addressed còn lại là authority, không phải
  biến thể tạm của cùng một kết quả.

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
