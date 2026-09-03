# Project operating directive

> **2026-08-26 supersession:** the active ingestion/mapping architecture is
> [`docs/GEMINI_JSON_FIRST_PROJECT_GOAL.md`](docs/GEMINI_JSON_FIRST_PROJECT_GOAL.md).
> Sections below remain historical operating context only where they require
> PP-OCR/VietOCR/geometry or a frozen V3 reader. The current pipeline uses
> Gemini page→hierarchical JSON without those dependencies, then restarts
> mapping at Family 1. Git/S3/Codex, fail-closed and generalization policies
> remain in force.

> **2026-09-02 corpus/no-resubmit authority, expanded by the user:** the active
> source universe is now all 27 registered bank stock codes from **2024 through
> the current reporting period**. The earlier 8-bank Gemini corpus and the
> running 19-bank 2025-current frontier remain protected reuse-only inputs:
> their exact PDF/page/image identities must never be submitted again. The new
> user authority explicitly adds missing 2024 filings for all 27 banks,
> including 2024 filings of ACB, BID, CTG, HDB, MBB, VCB, VIB and VPB; it does
> not authorize a repeat of their existing 2025-current JSON. New paid requests
> are content-level missing pages only, through OpenRouter with the fixed model
> `google/gemini-3.7-flash`. Try `google-vertex/global/flex` first; when that
> exact Flex route is unavailable, use the cheapest compatible standard route
> (`google-ai-studio`, tier `standard` at this checkpoint). No model fallback
> or direct-Google API is allowed. Every run, resume and repair must reject an
> overlap with either protected corpus before its
> first provider request; bank code alone is no longer a sufficient
> no-resubmit key because one bank may have protected 2025 pages and genuinely
> new 2024 pages.

> **2026-09-02 Vietnamese-only page authority:** before any paid request, every
> PDF longer than 100 physical pages must pass a recorded language-boundary
> review. OCB filings require the same review regardless of length because a
> number of its PDFs append a complete English copy after the Vietnamese
> report. Only the Vietnamese physical-page prefix may enter `run`, `resume`
> or `repair`; excluded English pages must never be submitted merely to make a
> source PDF look page-complete. The exact per-file cutoffs are maintained in
> `docs/experiments/GEMINI_JSON_FIRST_USER_REQUIREMENTS.md`. A file without a
> verified cutoff is blocked before the first provider request.

> **2026-09-02 2024 restoration checkpoint:** the immutable S3 source snapshot
> contains 408 registered 2024 PDFs across all 27 bank codes. All 259 initially
> missing files were hydrated by content hash; all 408 local files now match
> the snapshot. The registered source inventory yields 308 content-unique
> Vietnamese full-BCTC candidates. Language-boundary review is complete for all
> seven 2024 PDFs over 100 physical pages and all twelve OCB PDFs: 228 appended
> English pages are excluded, leaving exactly 17,553 payable Vietnamese pages.
> The 2024 plan remains blocked from provider execution until the protected
> 2025-current ledger is completely successful and exact replay proves zero
> overlap with every existing/active Gemini page identity.

> **2026-09-03 controlled-cost fallback:** Vertex Flex remains the primary
> route. A typed Flex provider failure may fall through inside OpenRouter to
> the pinned cheapest standard Gemini 3.7 Flash endpoint, currently Google AI
> Studio standard. A completed/cached page is never submitted again during
> fallback. The sealed request must record the exact provider allowlist/order;
> each completed page records the provider and tier OpenRouter selected plus
> actual cost. OpenRouter does not expose a separate internal Flex-error body
> when it succeeds on the next allowed route, so no such receipt may be
> invented. Priority tier, another model, arbitrary provider routing and direct
> Google calls remain forbidden.

> **2026-08-27 prompt/algorithm directive:** keep Gemini prompts short, fixed and
> structurally focused. Gemini supplies visible observations; deterministic code
> owns normalization, graph construction, period/unit resolution, equations and
> mapping. Do not require the model to echo untouched data or satisfy family
> logic. Escalation is automatic and limited to a small predeclared prompt set
> for typed missing-row, column-width or missing-context failures; never tune a
> prompt interactively per bank/file/page. A validator must preserve usable
> mappings and canonicalize harmless representation drift instead of rejecting
> correct evidence to force one preferred serialization.

> Authority: user-supplied high-level objective and current operating tactics.
> This file is the standing prioritization reference for every execution turn.
> Read it together with `PROJECT_GOAL.md`; where older queues conflict, this
> directive controls current execution.

## 1. Mục tiêu cuối cùng của project

Mục tiêu không phải:

- tối đa số test GREEN;
- tối đa số artifact/hash/manifest;
- hoàn thiện riêng MBB/VPB;
- tối ưu reader vô hạn;
- chỉ tìm đúng statement boundary;
- chỉ tạo thật nhiều TABLE/ROW/CELL candidates;
- hay nghiên cứu vô hạn từng accounting family.

Mục tiêu cuối cùng là xây một hệ thống tổng quát, scalable và có khả năng xử lý BCTC ngân hàng chưa từng thấy:

```text
PDF BCTC
→ đọc đúng visible source evidence
→ hiểu cấu trúc tài liệu
→ xác định CDKT / KQKD / LCTT / TM
→ xác định đúng TABLE
→ nối TABLE qua nhiều trang
→ reconstruct logical ROW
→ xác định CELL / VALUE_POSITION
→ hiểu AXIS / DIMENSION
→ hiểu period / unit / scope
→ hiểu hierarchy và accounting context
→ chuẩn hóa vào universal schema
→ accounting validation
→ structured data
→ Excel
→ provenance đầy đủ
```

Hệ thống cuối cùng phải generalize trên:

- nhiều ngân hàng;
- nhiều kỳ;
- Q1/Q2/Q3/Q4/năm/bán niên;
- consolidated/separate;
- audited/reviewed/unaudited;
- scan/native/mixed;
- layout chưa từng dùng để development;
- filing chưa từng thấy.

Generalization trên unseen filing là KPI cuối cùng.

## 2. Current project position

Reader V3 đã hoàn thành và freeze.

Hiện đã có:

- 27 Wave-1 documents;
- 1,449 pages;
- OCR/native source evidence;
- word/line boxes;
- geometry;
- page graphs;
- candidate TABLE/ROW/CELL/AXIS;
- Role-B page hypotheses;
- Role-A Level-1 machine reference;
- multiple cross-bank research panels.

Nhưng hiện project vẫn chưa có broad accepted production structure:

```text
accepted STATEMENT
accepted TABLE
accepted LOGICAL_ROW
accepted VALUE_POSITION
accepted AXIS
accepted HIERARCHY
Wave-1 canonical mapping
Wave-1 mapped Excel
```

Do đó current bottleneck không còn là reader.

Current scientific problem là:

> Từ source evidence hiện có, làm thế nào suy ra đúng recurring financial-document structure xuyên nhiều ngân hàng, rồi chuyển structure đó thành canonical data/Excel?

## 3. V3 reader phải tiếp tục frozen

Không tạo V4/V3.1 hay mở rộng recovery/S3/reader infrastructure chỉ vì còn terminal/unresolved pages.

Chỉ reopen reader nếu downstream structural research chứng minh một lỗi:

- làm mất main statement;
- làm mất material table/row/value;
- làm sai period;
- làm sai unit;
- làm sai consolidated/separate scope;
- làm sai sign/material value;
- hoặc ảnh hưởng một recurring structural family đáng kể.

Nếu cần sửa:

- sửa generic;
- bounded;
- replay affected pages;
- không mặc định rerun toàn corpus;
- không relabel/overwrite V3.

## 4. Chiến thuật phát triển hiện tại: research-first

Không quay lại vòng lặp:

```text
small code change
→ full regression 4–5 hours
→ small fix
→ full regression again
```

Current development loop phải là:

```text
observe real PDFs
→ understand recurring structure
→ classify failures
→ form hypotheses
→ falsify cheaply
→ test cross-bank
→ extract generic abstractions
→ productionize winners
→ accepted structure
→ canonical mapping
→ validation
→ Excel
```

Nhưng cũng không được chuyển sang cực ngược lại:

```text
family research
→ family research
→ family research
→ endless panels
→ accepted structure remains zero
```

Research phải phục vụ việc xây pipeline.

## 5. Bắt buộc trực tiếp quan sát PDF thật

Không chỉ reasoning từ:

- JSON;
- coordinates;
- candidate counts;
- OCR text;
- test outputs.

Khi nghiên cứu một case, hãy xem kết hợp:

```text
rendered PDF pixels
+ OCR/native text
+ word/line bounding boxes
+ current table/row/cell/axis candidates
+ neighboring pages
+ current algorithm output
```

Câu hỏi đầu tiên luôn là:

> “Tại sao một người đọc BCTC biết cấu trúc đúng là gì?”

Sau đó mới chuyển human-visible cues thành machine-observable evidence.

Ví dụ:

Human cue: trang sau vẫn là continuation của cùng bảng.

Machine evidence:

```text
same accounting owner
+ compatible axes
+ same unit/scope
+ sibling sequence continues
+ no structural reset
+ compatible geometry
```

Không bắt đầu bằng arbitrary threshold.

## 6. Wave 1 phải học theo accounting/structural family xuyên ngân hàng

Wave 1 không được quay lại bank-by-bank depth-first.

Không làm:

```text
ACB hoàn thiện
→ MBB hoàn thiện
→ TCB hoàn thiện
→ ...
```

Đơn vị học chính là một recurring accounting/structural family được quan sát xuyên nhiều ngân hàng, cùng toàn bộ local context của nó.

Ví dụ:

```text
LOAN_QUALITY_CLASSIFICATION
LOAN_MATURITY_BUCKETS
CUSTOMER_LOAN_BORROWER_OR_SECTOR_BREAKDOWN
PROVISION_MOVEMENT_ROLLFORWARD
LIQUIDITY_RISK_MATURITY_GAP
CUSTOMER_DEPOSIT_TYPE_BREAKDOWN
CUSTOMER_DEPOSIT_TERM_BREAKDOWN
...
```

Ưu tiên:

```text
Family A across many banks
→ invariant + variants
→ generic mechanism

Family B across many banks
→ invariant + variants
→ generic mechanism

Family C across many banks
→ ...
```

## 7. Mỗi family phải được hiểu bằng local graph, không bằng label đơn lẻ

Một row/table không được hiểu chỉ bởi text.

Phải sử dụng khi source evidence cho phép:

- owner;
- parent;
- ancestor;
- children;
- siblings;
- previous row;
- next row;
- previous table;
- next table;
- note hierarchy;
- page before/after;
- continuation relation;
- axis roles;
- unit;
- period;
- scope;
- total/subtotal;
- accounting population;
- neighboring accounting families.

Ví dụ: `Nợ đủ tiêu chuẩn` đứng riêng là weak evidence. Nhưng:

```text
owner = customer loans
parent = loan-quality breakdown
siblings =
  special mention
  substandard
  doubtful
  loss
axes = two comparative monetary periods
total = same-population loan balance
neighbors = maturity / borrower / industry / provision
```

là một strong structural fingerprint.

## 8. Local Accounting Graph là abstraction trung tâm cần hướng tới

Current research đã lặp lại cùng một pattern:

```text
label-only
→ nhiều false positives

label
+ correct accounting owner
+ axis roles
+ sibling topology
+ local neighborhood
→ tốt hơn rõ rệt
```

Do đó không xây parser độc lập cho từng family. Hãy chủ động rút ra một generic Local Accounting Graph framework:

```text
LOCAL_ACCOUNTING_GRAPH

OWNER / POPULATION
│
├── BRANCH_ROLE
├── PARENT / CHILD
├── SIBLING_SET
├── ORDERED_CHILD_SET
├── TOTAL / SUBTOTAL
├── AXIS_ROLE
├── UNIT / PERIOD / SCOPE
├── PREVIOUS / NEXT
├── NEIGHBOR_TABLE
├── CONTINUATION_EDGE
└── OPTIONAL_VARIANT
```

Accounting families nên ngày càng trở thành configurations/instances của engine chung, không phải parser riêng.

Ví dụ `LOAN_QUALITY_CLASSIFICATION` có thể khai báo:

```text
owner = customer loans
branch role = credit quality
children = five ordered debt grades
axes = comparative monetary periods
closure = total equals same-population loan balance
neighbors = maturity / borrower / industry / provision
```

Trong khi `LOAN_MATURITY_BUCKETS` dùng cùng engine với branch role và child roles khác.

## 9. Luôn nghiên cứu cả positive, negative và matched controls

Không chỉ xem failures. Với mỗi hypothesis, phải có:

```text
true positives
+ similar-looking negatives
+ currently-correct controls
```

Một mechanism chỉ tốt nếu:

```text
fixes target failures
AND preserves controls
AND keeps false merges bounded
```

False merge thường nguy hiểm hơn abstention. Khi evidence không đủ: `abstain / unresolved`.

## 10. Text là evidence, không phải identity

Current research đã chứng minh cùng label có thể xuất hiện trong nhiều accounting families.

Do đó:

```text
same text != same accounting identity
```

Identity phải cân nhắc:

```text
statement
+ owner/parent
+ local hierarchy
+ sibling set
+ table role
+ axes
+ unit
+ period
+ scope
+ neighboring structure
```

Không global-match duplicate TM labels chỉ bằng text.

## 11. Geometry cũng chỉ là evidence

Geometry hữu ích cho alignment, row/column structure, table continuation, page orientation và boundaries.

Nhưng:

```text
geometry alone != table identity
geometry alone != accounting family
geometry alone != continuation truth
```

Numeric lanes cũng chỉ là evidence, không phải table authority. Use geometry inside a local evidence graph.

## 12. Page relationships phải được model rõ ràng

Không classify page độc lập khi cấu trúc trải qua nhiều trang.

Phân biệt:

```text
document continuation
note continuation
table continuation
row continuation
section continuation
```

Một page có thể:

- tiếp cùng note nhưng bắt đầu table mới;
- tiếp cùng table nhưng không lặp title;
- chứa cuối table A và đầu table B;
- chứa nhiều logical regions.

Dùng previous page, next page, previous table, next table, note hierarchy, axis continuity, unit continuity, row frontier và section reset làm evidence.

## 13. Học core invariant và legitimate variants

Mỗi family phải tách `CORE INVARIANT` khỏi `OPTIONAL / LEGITIMATE VARIANTS`.

Ví dụ loan quality có thể có core:

```text
customer-loan owner
five debt grades
comparative monetary axes
same-population total
```

và variants:

```text
optional margin/advance row
percentage columns
unlabeled total
inherited unit
title inherited from previous page
nested additional detail
```

Không hard-code variant theo bank, ép optional row vào core, hoặc tạo ID mới chỉ vì presentation khác.

## 14. Thứ tự mở rộng corpus

Ưu tiên:

1. many banks, same/similar period/report form → learn cross-bank invariants;
2. same families, different periods → temporal variation;
3. consolidated vs separate → scope variation;
4. quarter / half-year / annual → report-form variation;
5. audited / reviewed / unaudited + scan/native/mixed;
6. unseen holdout.

Cross-bank first là intentional. Không mix quá nhiều dimensions sớm nếu không có research question cụ thể.

## 15. Research family phải có maturity state và stop rule

Mỗi family theo dõi trạng thái:

```text
DISCOVERY
→ HYPOTHESIS
→ CROSS_BANK_SUPPORTED
→ STRUCTURALLY_MATURE
→ GENERIC_PRIMITIVES_EXTRACTED
→ READY_FOR_ACCEPTANCE
→ ACCEPTED / PRODUCTION_CANDIDATE
```

Một family nên dừng tiêu thụ thêm visual panels khi:

- core topology đã ổn định xuyên bank;
- hard controls đã được hiểu;
- false positives bounded;
- legitimate variants đã được phân loại;
- remaining uncertainty đã rõ;
- shared generic primitives đã rõ.

Khi đó dừng mở thêm panel chỉ để tăng sample và chuyển sang accepted structure / generic engine.

## 16. Research phải chuyển thành accepted structure

Hiện có rất nhiều candidates nhưng accepted structure vẫn bằng 0. Điều này không được kéo dài vô hạn.

Mỗi structurally mature family phải trả lời:

> “Source structure nào đã đủ bằng chứng để accept?”

Phải dần chuyển:

```text
candidate TABLE → accepted TABLE ownership
candidate ROW → accepted LOGICAL_ROW
candidate CELL → accepted VALUE_POSITION
candidate AXIS → accepted AXIS_ROLE
candidate relation → accepted PARENT/CHILD/SIBLING/CONTINUATION edge
```

Research progress phải cuối cùng tạo ra accepted graph.

## 17. Không tiếp tục nghiên cứu family như các silo độc lập

Sau mỗi vài family, hỏi: những quan hệ nào lặp lại và nên trở thành generic primitives?

Candidate shared primitives có thể gồm:

```text
OWNER_RESOLUTION
PARENT_CHILD_EDGE
ORDERED_SIBLING_SET
AXIS_ROLE
COMPARATIVE_PERIOD_AXIS
UNIT_SCOPE_EDGE
SECTION_DEFAULT
TABLE_CONTINUATION
NOTE_CONTINUATION
ROW_FRONTIER
TOTAL_SUBTOTAL
SAME_POPULATION_CLOSURE
MOVEMENT_ROLLFORWARD
NEIGHBOR_RELATION
OPTIONAL_CHILD
STRUCTURAL_RESET
```

Không coi danh sách này là final. Chỉ promote primitive nếu source evidence từ nhiều families/banks hỗ trợ. Nếu bốn family đều cần `OWNER_RESOLUTION`, không implement bốn versions riêng.

## 18. Statement discovery và lower-level structure có thể hỗ trợ lẫn nhau

Không cần statement classification hoàn hảo trước khi table research. Evidence có thể đi hai chiều.

Ví dụ:

- recognized loan-quality family → strong evidence page belongs to TM;
- recognized balance-sheet topology → strong CDKT evidence.

Dùng lower-level structure để corroborate statement boundaries, nhưng preserve provenance và không circularly force truth.

## 19. Tách Development / Prospective Validation / Holdout

Không để yêu cầu “fresh pixel” làm research bị kẹt.

Phân biệt:

- **DEVELOPMENT / RESEARCH:** được reuse case đã xem để understand, prototype, falsify và regression.
- **PROSPECTIVE VALIDATION:** phải fresh trước scoring nếu claim là prospective.
- **FINAL HOLDOUT:** phải untouched và không được dùng development.

Nếu không còn provably unopened case trong Wave 1, vẫn được tiếp tục research bằng viewed cases, nhưng label evidence đúng là `DEVELOPMENT/REPLAY`; không được gọi là fresh validation.

Không dừng học một family quan trọng chỉ vì không còn fresh page.

## 20. Test strategy: 3 tiers

### Tier 1 — Fast

Synthetic + 10–30 representative real cases. Mục tiêu: vài phút. Dùng để falsify hypothesis nhanh.

### Tier 2 — Cross-bank

Aim roughly 5–10 banks và khoảng 100–300 relevant cases where feasible, bao gồm positives, hard negatives, matched controls, scan/native/mixed, simple/complex và continuation/non-continuation.

Chỉ productionize nếu Tier 2 cho measurable cross-bank benefit.

### Tier 3 — Broad/full replay

Chỉ khi:

- mechanism đã generic;
- Tier 1 pass;
- Tier 2 hỗ trợ;
- false positives bounded;
- mechanism chuẩn bị productionize.

Trước bất kỳ multi-hour run nào, phải ghi:

```text
HYPOTHESIS:
WHAT WOULD FALSIFY IT:
WHY TIER 1 IS INSUFFICIENT:
WHY TIER 2 IS INSUFFICIENT:
WHAT NEW INFORMATION TIER 3 WILL PRODUCE:
```

Nếu smaller run có thể trả lời thì không chạy Tier 3. Full replay là evaluation tool, không phải default development loop.

## 21. Role A isolation

Research workflow:

```text
PDF/source
→ blind observation
→ hypothesis
→ blind prediction
→ freeze result
→ only then compare Role A
```

Role A không được dùng để chọn threshold, candidate, boundary, continuation, tune family detector hoặc chọn schema ID. Role A chỉ là diagnostic machine reference. Không gọi Role-A agreement là human accuracy.

## 22. Không hard-code

Production logic không được route theo:

```text
bank == ...
filename == ...
page == ...
bank-specific note number
```

Bank/page/note được phép dùng cho provenance, debugging và research reporting; không dùng làm inference rule. Logic phải dựa trên source-observable structural/accounting evidence.

## 23. Schema chỉ đến sau accepted source structure

Không map schema khi structure còn không chắc.

Đúng thứ tự:

```text
source row
+ table role
+ owner
+ parent
+ siblings
+ axes
+ period
+ unit
+ scope
+ local accounting context
↓
canonical identity
```

Quy tắc:

```text
same accounting meaning → reuse ReportNormId
different wording → alias
presentation-only difference → no new ID
axis/dimension/header → no accounting ID
genuine different accounting meaning → new-ID proposal
insufficient evidence → unresolved
```

Không tạo ID chỉ để tăng coverage.

## 24. Schema phải hội tụ

Current:

```text
BASE_SCHEMA = 1,593
UNIVERSAL_SCHEMA = 1,935
```

1,935 không phải mục tiêu càng lớn càng tốt.

Goal: smallest reasonable canonical ontology that preserves genuine accounting distinctions and maximizes cross-bank comparability.

Theo dõi genuine new IDs, aliases, duplicate candidates, presentation-only rows, unresolved gaps, new IDs / 1,000 source rows và alias:new-ID ratio.

Qua các wave:

```text
coverage ↑
comparability ↑
new-ID rate ↓
```

Nếu new-ID rate không giảm, audit canonicalization trước khi append tiếp.

## 25. Accounting validation chỉ corroborate/veto

Accounting equations được dùng để corroborate, detect inconsistency và veto impossible mapping.

Không dùng để invent values, silently repair OCR, choose structure solely because arithmetic closes hoặc convert blank to zero without source evidence.

Preserve states:

```text
OBSERVED_VALUE
OBSERVED_ZERO
DASH
BLANK
NOT_OBSERVED
NOT_APPLICABLE
AMBIGUOUS
UNRESOLVED
```

## 26. Bắt đầu bounded end-to-end vertical slices sớm

Không chờ hiểu toàn bộ TM rồi mới thử mapping.

Khi một số families đã structurally mature, chọn nhiều banks và chạy bounded vertical slices:

```text
PDF/source evidence
→ accepted TABLE
→ accepted ROW
→ accepted CELL
→ accepted AXIS
→ hierarchy/context
→ schema mapping
→ accounting validation
→ structured output
```

Đây chưa phải full-document production approval. Mục tiêu là kiểm tra các generic structural abstractions hiện tại có thực sự đủ để đi đến canonical data/Excel không.

Nếu vertical slice fail ở mapping/context thì quay lại structural model với evidence cụ thể.

## 27. Near-term milestone phải là generic engine + accepted structure

Không coi milestone tiếp theo là thêm 20 family panels hay replay đủ 1,422 adjacent pairs.

Desired next milestone:

```text
Generic Local Accounting Graph v1
tested across multiple families
and multiple banks
↓
first accepted TABLE ownership
↓
first accepted LOGICAL_ROW sets
↓
first accepted AXIS roles
↓
first accepted HIERARCHY edges
↓
first bounded multi-bank end-to-end vertical slices
```

Báo accepted counts riêng cho CDKT, KQKD, LCTT và TM. Không mix candidate counts với accepted counts.

## 28. Coverage phải bao phủ toàn bộ bốn statement groups

139 Role-A blocks chỉ là Level-1 discovery benchmark.

Mục tiêu thật là CDKT, KQKD, LCTT và TM đến:

```text
STATEMENT
→ TABLE
→ LOGICAL_ROW
→ CELL/VALUE_POSITION
→ AXIS
→ HIERARCHY
→ EVIDENCE
```

Đặc biệt TM phải được khảo sát toàn bộ phần định lượng. Biết boundary TM không được coi là TM coverage.

Theo dõi riêng statement blocks, tables, rows, value positions, axes, continuation structures, hierarchy, unresolved regions, source-accounted rate và canonical-mapped rate.

## 29. Failure handling phải theo archetype, không theo bank

Khi gặp lỗi case A/B/C, không sửa từng case. Cluster thành failure archetype, sau đó:

```text
generic mechanism
→ bounded replay
→ measure cross-bank delta
```

Mỗi fix báo:

```text
banks improved
documents improved
pages improved
tables affected
rows/value positions affected
false merges
new ambiguities
unresolved preserved
```

## 30. Expected progress reports

Status từ đây nên ưu tiên:

```text
Inspected:
X banks / Y pages / Z regions

Discovered:
N recurring accounting/structural families

Family A:
observed in X banks
core topology ...
variants ...
counterexamples ...

Hypothesis H1:
rejected because ...

Hypothesis H2:
Tier-1 ...
Tier-2 ...

Shared primitives extracted:
OWNER_RESOLUTION
AXIS_ROLE
...

Accepted:
TABLE = ...
ROW = ...
VALUE_POSITION = ...
AXIS = ...
HIERARCHY = ...

Vertical slices:
X families / Y banks
→ canonical output ...
```

Ít tập trung hơn vào hundreds of tests GREEN, hashes, manifests và hours of replay. Tests vẫn quan trọng nhưng là protection/evaluation evidence, không phải project objective.

## 31. Stop rules

Dừng và quay lại visual/source research nếu:

- multi-hour run không có clear information gain;
- implementation tăng nhanh hơn hiểu biết source structure;
- geometry-only mechanism có nhiều visual counterexamples;
- một mechanism chỉ hoạt động ở 1–2 banks;
- Role A bắt đầu leak vào blind inference;
- có bank/page/title hard-code;
- candidate counts tăng nhưng accepted structure không tăng.

Ngược lại, dừng mở thêm research panels và chuyển sang productionization nếu:

- family core topology đã ổn định;
- controls đã hiểu;
- variants đã classified;
- generic primitives đã rõ;
- thêm panels không còn thay đổi abstraction đáng kể.

## 32. Immediate execution priority

Ngay bây giờ:

1. Giữ V3 frozen.
2. Không chạy deferred all-1,422 publisher.
3. Tiếp tục high-information cross-bank family research hiện tại.
4. Ưu tiên family recurrence trên nhiều banks trước cross-period variation.
5. Với mỗi family, học local graph đầy đủ: owner; parent/child; siblings; neighbors; axes; page relations; continuation; variants.
6. Đồng thời rà các family đã nghiên cứu: loan quality; loan maturity; borrower/sector; provision movement; liquidity maturity gap; unit scope; statement/page continuation để tìm shared generic primitives.
7. Bắt đầu thiết kế/đánh giá Generic Local Accounting Graph v1 từ evidence đã có.
8. Khi family đủ mature, dừng panel expansion và chuyển nó thành accepted structure.
9. Khi có vài mature families, chạy bounded multi-bank vertical slices đến schema/validation/output.
10. Chỉ sau khi generic mechanisms có Tier-2 support mới productionize và chạy Tier-3/full replay.

Không chờ user approval cho routine engineering decisions. Chỉ hỏi user khi có genuine accounting/schema ambiguity mà source/cross-bank evidence không giải quyết được.

## 33. Mục tiêu dài hạn phải luôn được giữ trong đầu

Primary loop:

```text
SOURCE PDFs
↓
cross-bank observation
↓
accounting/structural family discovery
↓
local accounting graph
↓
generic structural primitives
↓
accepted structure
↓
schema canonicalization
↓
accounting validation
↓
structured data / Excel
↓
new banks / periods / scopes
↓
failure analysis
↓
generic improvement
```

Mỗi vòng phải hướng tới:

```text
accepted structural coverage ↑
canonical coverage ↑
cross-bank reuse ↑
unseen-filing generalization ↑

bank-specific assumptions ↓
recurring unresolved failures ↓
unnecessary schema IDs ↓
```

## 34. Final project success criterion

Thành công cuối cùng không phải all tests GREEN mà là một BCTC ngân hàng chưa từng thấy có thể đi qua pipeline:

```text
PDF
→ source structure
→ TABLE/ROW/CELL/AXIS
→ accounting context
→ canonical schema
→ validation
→ Excel
```

với:

- provenance đầy đủ;
- không hard-code bank;
- không silent coercion;
- explicit uncertainty;
- accuracy được chứng minh trên unseen holdouts.

Mọi quyết định kỹ thuật từ thời điểm này phải được đánh giá bằng câu hỏi:

> Việc này có đưa project gần hơn tới generalizable unseen-bank PDF → accurate standardized BCTC → validated Excel hay không?

Nếu không, hãy xem lại priority.

Tiếp tục execution ngay theo critical path này; không dừng để viết thêm một strategy document khác.

## 35. Family-sweep rule — breadth across accounting families

Đây là execution rule bổ sung; nó không thay thế các directive phía trên.

Sau khi `Generic Local Accounting Graph v1` chứng minh được khả năng dùng chung
trên ít nhất `LOAN_QUALITY_CLASSIFICATION` và `LOAN_MATURITY_BUCKETS`, không tiếp
tục đào sâu một family chỉ để đạt gần 100% coverage.

Mục tiêu tiếp theo là **quét lần lượt các accounting/structural family xuyên
nhiều ngân hàng**.

Vòng lặp mặc định:

```text
select one recurring accounting family
→ inspect real PDF/source evidence across multiple banks
→ compare positives + matched controls + variants
→ reuse existing Local Accounting Graph primitives
→ add/modify a generic primitive only if genuinely missing
→ accept the strict subset supported by evidence
→ preserve ambiguous/rare variants as UNRESOLVED
→ map accepted structure to schema
→ validate values/relationships
→ record family coverage
→ MOVE TO NEXT FAMILY
```

Không biến mỗi family thành một research project độc lập.

### 35.1. Progressive reuse is mandatory

Mỗi family mới phải bắt đầu bằng câu hỏi:

> Những primitive hiện có đã giải quyết được bao nhiêu phần của family này?

Ưu tiên reuse:

```text
OWNER_RESOLUTION
PARENT_CHILD_EDGE
ORDERED_SIBLING_SET
AXIS_ROLE
COMPARATIVE_PERIOD_AXIS
UNIT_SCOPE_EDGE
TOTAL_SUBTOTAL
SAME_POPULATION_CLOSURE
NEIGHBOR_RELATION
TABLE_CONTINUATION
ROW_FRONTIER
STRUCTURAL_RESET
```

Không tạo parser riêng theo family nếu cùng structural mechanism đã tồn tại.

Càng nhiều family được học, lượng code/logic mới cho mỗi family phải có xu hướng
giảm. Nếu family thứ 10 vẫn cần một pipeline hoàn toàn riêng như family thứ nhất,
dừng và kiểm tra abstraction.

### 35.2. Do not wait for 100% family completion

Cho phép:

```text
ACCEPTED_CORE
ACCEPTED_OPTIONAL_VARIANT
UNRESOLVED_VARIANT
UNRESOLVED
```

Ví dụ nếu:

```text
22 banks accepted
3 banks accepted with optional variants
2 banks unresolved
```

thì không giữ toàn family lại chỉ để giải 2 bank cuối.

Preserve unresolved evidence and move on. Sau khi breadth sweep đủ rộng, cluster
residual failures xuyên nhiều family và giải bằng generic mechanisms.

### 35.3. Structure first, schema immediately after strict acceptance

Không map schema trước khi structure rõ. Nhưng cũng không chờ toàn bộ TM hoàn
thành mới map.

Với mỗi accepted family:

```text
accepted TABLE
→ accepted logical ROW
→ accepted AXIS / UNIT / PERIOD / SCOPE
→ accepted hierarchy
→ canonical schema mapping
→ accounting validation
→ extracted values
```

Sau đó chuyển family tiếp theo. Schema coverage phải tăng song song với accepted
structural coverage.

### 35.4. Maintain a Family Coverage Board

Theo dõi tối thiểu:

```text
Family
Banks inspected
Banks with source occurrence
Accepted banks
Unresolved banks

Accepted TABLE
Accepted LOGICAL_ROW
Accepted VALUE_POSITION
Accepted AXIS
Accepted HIERARCHY

Schema mapped rows
New-ID proposals
Aliases
Unresolved schema gaps
Validated value axes
```

Ví dụ:

```text
LOAN_QUALITY             27   25 present   22 accepted   3 unresolved
LOAN_MATURITY            27   24 present   21 accepted   3 unresolved
CUSTOMER_DEPOSIT_TYPE    ...
SECURITIES               ...
PROVISION_MOVEMENT       ...
```

Project progress should increasingly be measured by this board, not by test
count, candidate count or experiment count.

### 35.5. Prioritize broad financial-statement coverage

After the first two acceptance families, continue across recurring BCTC clusters
such as:

```text
cash / central-bank deposits
interbank deposits and loans
trading / AFS / HTM securities
customer loans
loan quality
loan maturity
borrower / economic sector
loan provision
customer deposits
deposit type / term / depositor class
issued papers
borrowings
fixed assets
other assets / liabilities
equity movements
interest income / expense
fees
FX
securities income
other operating income/expense
liquidity risk
repricing risk
currency risk
other recurring TM families
```

Danh sách này chỉ mang tính minh họa, không phải processing order hard-coded.

Chọn family tiếp theo bằng:

```text
prevalence across banks
× accounting importance
× source evidence availability
× reuse of existing primitives
× expected coverage gain
```

### 35.6. Stop excessive family-specific research

Stop and move on when:

- core topology is stable across several banks;
- matched controls establish the accounting role;
- a strict accepted subset is possible;
- remaining failures are rare variants rather than a missing generic core mechanism.

Do **not** launch repeated prospective protocols/full-document batches solely to
perfect one family unless the unresolved mechanism is expected to improve many
other families.

Net-interest is an example of a useful failure archetype, but do not repeat that
depth of experimentation for every TM family.

### 35.7. Residuals are solved after breadth

After a meaningful breadth sweep:

```text
collect all UNRESOLVED_VARIANT / UNRESOLVED cases
→ cluster by structural failure
→ identify shared missing primitives
→ implement generic fixes
→ replay only affected families
```

This is preferable to fully solving each family before moving forward.

### 35.8. Desired velocity

The expected pattern is:

```text
early families:
more observation + primitive creation

middle families:
mostly primitive reuse + family configuration

later families:
fast recognition / acceptance / mapping
```

Development speed per recurring family should improve over time.

### 35.9. Immediate instruction

Complete the current bounded `Generic Local Accounting Graph v1` acceptance work
on Loan Quality and Loan Maturity. Then start a **family sweep**.

Do not open another deep family-specific research branch by default. For every
next family:

```text
observe
→ reuse primitives
→ accept strict subset
→ map
→ record unresolved
→ next family
```

The near-term goal is not one perfect family. The near-term goal is:

> rapidly increasing accepted structural + canonical coverage across the major
> recurring BCTC families of many banks, using one increasingly reusable generic
> engine.
