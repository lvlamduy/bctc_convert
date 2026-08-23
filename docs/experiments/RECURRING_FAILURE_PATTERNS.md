# Recurring failure-pattern registry

Updated: 2026-08-23 (UTC)

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
  reset giả.
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
- **Status:** `MITIGATED`; final authority gate còn cần full replay, nhưng không
  được lặp multiplicatively hoặc trong inner loop.

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
- Chỉ mở lại full sweep sau khi revision/spec thực sự đổi (hoặc source drift độc
  lập được chứng minh), focused + adversarial + targeted panels đều xanh, và
  telemetry cho thấy stage nằm trong budget. Full build/verify là release gate,
  không phải vòng debug.
