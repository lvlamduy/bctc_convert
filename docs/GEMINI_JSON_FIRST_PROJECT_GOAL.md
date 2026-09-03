# Goal: Gemini JSON-first cho BCTC ngân hàng

## Goal statement để giao cho agent

> Thay thế đường đọc BCTC đang dùng PP-OCR 6, VietOCR và geometry bằng một
> pipeline Gemini JSON-first: render từng trang PDF đủ nét, dùng Gemini 3.7
> Flash trên Google Vertex để trả JSON nhiều tầng schema-blind, giữ nguyên
> chính tả, source order, hierarchy, header, period, unit và mọi giá trị nhìn
> thấy; số hóa cả CDKT, KQKD, LCTT và thuyết minh, còn trang không có nội dung
> tài chính liên quan phải trả disposition tối thiểu. Lưu raw/canonical/
> normalized/numeric/graph versions của toàn bộ page JSON vào database có index
> và cache content-addressed. Sau đó tiếp tục xử lý lần lượt từng accounting
> family bằng các thuật toán local accounting graph hiện có: truy hồi bounded
> region theo hai anchor parent-child hoặc sibling-sibling, tăng lên ba anchor
> khi chưa duy nhất, xét ancestor/parent/child/sibling/order/neighbor/page
> continuation/period/unit/scope, rồi dùng exhaustive multi-level subtotal và
> direct-frontier accounting equations để kiểm tra hoặc suy luận quan hệ. Không
> hard-code theo bank/file/page/value, không quét toàn database trong inner loop,
> không dùng phương trình để sửa source digit và không fallback sang OCR hay
> geometry cũ. Trước full-corpus ingestion phải benchmark nhiều prompt ngắn/dài,
> đơn giản/phức tạp, JSON schema, loại trang, DPI và repeat; chọn contract bằng
> exact label/value/hierarchy accuracy, determinism, latency, token và chi phí.

Phần còn lại của tài liệu là execution contract và definition of done cho goal
statement trên.

### Phạm vi corpus đang mở rộng (checkpoint 2026-09-01)

- Phạm vi thời gian: **Quý 1/2025 đến hiện tại**.
- Ma trận theo dõi gồm đủ 27 ngân hàng, nhưng paid provider frontier chỉ gồm 19
  ngân hàng mới: ABB, BAB, BVB, EIB, KLB, LPB, MSB, NAB, NVB, OCB, PGB, SGB,
  SHB, SSB, STB, TCB, TPB, VAB và VBB.
- ACB, BID, CTG, HDB, MBB, VCB, VIB và VPB đã có Gemini JSON hiện hành. Tất cả
  dữ liệu của tám ngân hàng này phải lấy từ manifest/store/cache đã xác thực;
  không gửi lại OpenRouter. PDF mới ngoài manifest của tám ngân hàng này chỉ
  được ghi vào inventory và chờ quyền riêng của người dùng.
- Mọi request API mới đi duy nhất qua OpenRouter, model
  `google/gemini-3.7-flash`, provider `google-vertex/global/flex`, service tier
  `flex`; direct Google và mọi fallback provider/model đều bị vô hiệu hóa.
- Theo bổ sung ngày 2026-09-03, Agy trên VPS được chạy song song như một
  execution route riêng cho page chưa có JSON: dùng cùng ảnh/prompt/schema và
  validator, bắt đầu bằng `gemini-3.7-flash-low`, chỉ tăng Medium rồi High khi
  output trước chưa dùng được. Mỗi PDF phải được claim khỏi hàng đợi Vertex Flex
  trước khi Agy chạy; provider/model/effort phải lưu đúng thực tế. Gemini 3.8
  Flash High chỉ review chiến lược, không làm reader cho corpus.
- Denominator đã xác thực ở checkpoint: corpus cũ **140 PDF / 8.947 trang** chỉ
  tái sử dụng; frontier mới **271 PDF / 14.947 trang**. Runner phải chứng
  minh paid frontier không chứa ACB/BID/CTG/HDB/MBB/VCB/VIB/VPB trước request
  đầu tiên.

## 1. Mục tiêu duy nhất

Xây dựng pipeline tổng quát, có thể mở rộng và chạy được trên BCTC ngân hàng
chưa từng thấy, theo kiến trúc mới:

```text
PDF BCTC bất biến
→ render từng trang thành ảnh đủ nét
→ pilot: Gemini 3.7 Flash qua OpenRouter, khóa Google Vertex Flex
→ corpus hiện hành: Gemini 3.7 Flash qua OpenRouter Google Vertex Flex và worker
  Agy disjoint; không gọi Google API, không gửi trùng page
→ JSON nhiều tầng, schema-blind, giữ nguyên chữ và giá trị nhìn thấy
→ JSON/database được version hóa và lập chỉ mục
→ truy hồi vùng ứng viên nhỏ theo từng accounting family
→ local accounting graph + hierarchy + phương trình kế toán
→ mapping vào UNIVERSAL_BANK_BCTC_SCHEMA
→ structured data / Excel / provenance / unresolved
```

Gemini là reader duy nhất của đường xử lý mới. Tuyến API được khóa đúng
`google/gemini-3.7-flash` và OpenRouter provider
`google-vertex/global/flex`, tắt mọi provider/model fallback. Worker Agy được
phép cung cấp cùng Gemini 3.7 Flash trên một frontier đã claim riêng, với effort
`low → medium → high` chỉ theo thất bại semantic/schema; đây không phải fallback
provider ẩn và phải lưu provenance Agy riêng. Từ ngày
2026-08-27, hai credential Google không còn ngân sách nên phần corpus còn lại
chạy **OpenRouter-only**: không gọi Google standard, Google Batch hay Google
fallback. Tham số đường dẫn key Google có thể còn xuất hiện trong CLI để tương
thích ngược, nhưng child request bắt buộc mang `google-standard-mode=disabled`
và không được sử dụng key đó. Các page-version Google đã hoàn thành trước thời
điểm chuyển route vẫn được giữ bất biến trong database; khi cùng một
source/image/prompt/schema có cả Google, OpenRouter hoặc Agy version thì manifest
hiện hành ưu tiên `OPENROUTER/flex`, sau đó Agy Low/Medium/High rồi mới đến các
version lịch sử; không xóa version nào. Mọi request phải
resume theo document/page, không submit trùng, và chỉ retry từ failure receipt
có kiểu rõ ràng. Không được cố ý gửi request vô ích chỉ để đốt quota.

Không sử dụng PP-OCR 6,
VietOCR, OCR fusion, word/line bounding box hoặc thuật toán phụ thuộc geometry
để đọc chữ, dựng dòng, dựng cột, nhận diện bảng hay quyết định mapping. Mã cũ
được giữ nguyên để tái lập các artifact lịch sử, nhưng không được gọi làm
fallback trong pipeline mới.

Các thuật toán family, ordered graph mapping, local accounting graph,
parent/child/sibling/neighbor matching, subtotal closure, direct-frontier
equations, period/unit/scope validation và fail-closed gates đã phát triển đến
hiện tại phải được tái sử dụng hoặc tổng quát hóa. Thay đổi chính là đầu vào của
chúng trở thành JSON nhiều tầng do Gemini đọc trực tiếp từ toàn bộ ảnh trang,
thay vì OCR rời rạc và geometry.

## 2. Source và ranh giới thẩm quyền

- PDF gốc và ảnh render nguyên trang vẫn là source bất biến cuối cùng.
- JSON Gemini là bản chép có cấu trúc từ source, không phải schema mapping và
  không tự có quyền sửa dữ liệu kế toán.
- Mọi JSON phải bind với SHA-256 PDF, số trang vật lý, SHA-256 ảnh, DPI/kích
  thước render, model ID chính xác, route OpenRouter Vertex Flex hoặc Google
  Batch trực tiếp, prompt version/hash,
  response-schema version/hash, raw response hash, token usage và chi phí.
- Không đưa ReportNormId, giá trị kỳ vọng, tên ngân hàng, ordinal tài liệu hoặc
  đáp án family vào prompt OCR.
- Không sửa chính tả, dấu câu, chữ số, dấu âm, dấu phần trăm, dấu phân cách hoặc
  giá trị nhìn thấy. Dữ liệu suy ra phải ở lớp riêng và không được thay thế raw
  output. Riêng dash kế toán và printed zero có thể cùng chiếu thành numeric
  coefficient zero; khác biệt lexical này không làm hỏng trang nhưng vẫn được
  ghi trong raw/canonical versions.
- Mọi thiếu, mâu thuẫn hoặc nhiều cách hiểu không phân giải được phải trở thành
  `UNRESOLVED`; không quay lại OCR/geometry cũ để cưỡng ép kết quả.

## 3. Phạm vi nội dung phải số hóa

Gemini xử lý độc lập từng trang và trả một trong các trạng thái đóng:

1. `NO_RELEVANT_FINANCIAL_CONTENT`: không có khoản mục BCTC, bảng BCTC hoặc
   thuyết minh tài chính cần số hóa;
2. `PRIMARY_FINANCIAL_STATEMENT`: có Bảng cân đối kế toán, Báo cáo kết quả kinh
   doanh, Báo cáo lưu chuyển tiền tệ hoặc bảng chính tương đương;
3. `FINANCIAL_NOTE_CONTENT`: có tiêu đề, khoản mục, bảng hoặc nội dung thuyết
   minh tài chính;
4. `MIXED_FINANCIAL_CONTENT`: một trang chứa nhiều vùng thuộc các loại trên;
5. `UNRESOLVED_PAGE`: ảnh có dấu hiệu liên quan nhưng model không thể xuất cấu
   trúc an toàn.

Trang không liên quan phải trả đúng một JSON tối thiểu, ví dụ:

```json
{
  "status": "NO_RELEVANT_FINANCIAL_CONTENT",
  "sections": [],
  "completion": {
    "all_relevant_content_transcribed": true,
    "uncertainty_exact": []
  }
}
```

Điều này giảm output token nhưng không làm input token bằng không: ảnh và prompt
vẫn bị tính phí. Hệ thống phải giảm chi phí bằng cache content-addressed và
không gọi lại trang có cùng page-image hash + model + prompt + schema.

Các trang có nội dung tài chính phải giữ:

- tiêu đề/note/section và quan hệ nhiều tầng;
- bảng và thứ tự bảng trên trang;
- header nhiều tầng, period, unit, scope và loại cột;
- row theo source order;
- `label_exact`, `row_kind`, `hierarchy_path` và quan hệ
  parent/child/sibling/previous/next;
- mọi value dưới dạng chuỗi nhìn thấy nguyên văn, gồm blank, dash, zero,
  negative và percent;
- subtotal/total có nhãn hoặc không nhãn;
- continuation với trang trước/sau khi model quan sát được, dưới dạng proposal
  để tầng document graph kiểm tra;
- narrative tài chính cần thiết để xác định owner, population, accounting scope
  hoặc ý nghĩa bảng.

Không yêu cầu và không dùng tọa độ/bounding box trong contract sản xuất. Page
number và source order là locator đủ cho pipeline mới.

## 4. Thử nghiệm prompt bắt buộc trước khi chạy corpus

Không chạy toàn bộ PDF trước khi hoàn thành một prompt evaluation có ground
truth. Ma trận thử nghiệm phải bao gồm:

- prompt ngắn, vừa và chi tiết;
- chỉ instruction, instruction + invariants, instruction + JSON Schema và một
  số lượng ví dụ tối thiểu;
- một pass so với classify-then-extract nếu cần;
- trang CDKT, KQKD, LCTT;
- bảng thuyết minh flat, nested, nhiều subtotal, grand total và continuation;
- bảng nhiều tầng header, nhiều period/unit, nhiều bảng trên cùng trang;
- trang scan rõ, mờ, nghiêng, có stamp, born-digital và mixed;
- trang có text tài chính nhưng không có bảng;
- trang hoàn toàn không liên quan;
- trang có unlabeled subtotal, blank, dash, zero, negative, discount,
  nonadditive row và alternative view;
- nhiều lần chạy lặp lại trên cùng ảnh ở 200 và 300 DPI; không dùng DPI thấp hơn.

Mỗi biến thể phải đo tối thiểu:

- JSON-schema validity;
- page-type precision/recall;
- exact visible-row recall và duplicate/hallucinated-row count;
- exact label-character accuracy;
- exact value-cell accuracy, ưu tiên tuyệt đối chữ số/dấu;
- header/period/unit/scope accuracy;
- hierarchy/parent/sibling/source-order accuracy;
- số phương trình exact đóng đúng và số phương trình đóng sai;
- repeat consistency;
- input/output/reasoning token, chi phí, latency và lỗi provider.

Prompt thắng phải giữ schema thống nhất và đạt gate đã công bố trên positive,
negative và matched controls. Không chọn prompt chỉ vì một trang đẹp. Không
chạy full corpus nếu còn lỗi đổi digit, chuyển value sang row/cột khác, bỏ row,
gộp bảng hoặc invent hierarchy trên panel khó.

Trang dài phải có riêng một completion/truncation gate: request cho phép tối đa
65.536 output token, provider phải kết thúc bình thường và `completion` đứng sau
toàn bộ `sections`. Model chỉ xác nhận complete và liệt kê uncertainty; code tự
đếm section/table/row/value-cell/populated-cell từ mảng thật. Model không dám
xác nhận complete, có uncertainty hoặc thiếu đuôi thì fail-closed; không dùng
self-count của model làm tín hiệu vì pilot đã chứng minh nó không ổn định.

## 5. Contract JSON nhiều tầng

Contract phải schema-blind và dùng cấu trúc ổn định, tối thiểu gồm:

```text
DOCUMENT
└── PAGE
    ├── status / page_type
    ├── SECTION / NOTE / STATEMENT
    │   ├── title_exact
    │   ├── owner / scope proposal
    │   ├── TABLE
    │   │   ├── ordered column/header tree
    │   │   └── ordered row tree
    │   │       ├── label_exact
    │   │       ├── row_kind
    │   │       ├── hierarchy_path
    │   │       ├── values_exact[]
    │   │       └── child rows
    │   └── relevant narrative blocks
    └── continuation proposals
```

JSON phải phân biệt rõ:

- `null` với chuỗi rỗng;
- blank với dash, printed zero và not observed;
- labeled subtotal với unlabeled subtotal;
- visible node với derived node;
- additive child, nonadditive child, adjustment và alternative presentation;
- current/prior period, money/percent/quantity và scale/unit;
- exact source string với normalized/parsed derivative.

Một visible row chỉ được xuất hiện một lần trong cùng table population. Gemini
không được dùng phép cộng để sửa số hoặc tạo label không nhìn thấy. Phương trình
trong bước OCR chỉ được dùng làm self-check và phải giữ nguyên mọi source value.

## 6. Database, versioning và index

Không lưu toàn bộ tài liệu chỉ như một JSON blob lớn rồi quét lại cho từng
family. Database phải giữ cả canonical artifact và các projection đã materialize:

- `document`: document hash, bank metadata không có quyền OCR, source manifest;
- `page`: document/page identity, image hash và page classification;
- `extraction_run`: model/provider/prompt/schema/settings/tokens/cost/status;
- `page_json_version`: raw response và canonical validated JSON bất biến;
- `section`, `table`, `column_node`, `row_node`, `value_cell`: projection để
  query nhanh;
- `hierarchy_edge`, `neighbor_edge`, `continuation_edge`: graph cục bộ;
- `numeric_view`: exact source string, parsed coefficient/scale/sign và parse
  disposition;
- `family_candidate_region`: cache shortlist theo family-spec/content root;
- `family_mapping_version`: candidates, winner/runner-up, equations, receipts,
  unresolved và provenance.

Không overwrite version cũ. Mỗi lớp sau phải bind hash/version của lớp trước:

```text
RAW_PROVIDER_RESPONSE
→ CANONICAL_PAGE_JSON
→ NORMALIZED_SEARCH_VIEW
→ TYPED_NUMERIC_VIEW
→ DOCUMENT_ACCOUNTING_GRAPH
→ FAMILY_CANDIDATE_REGION
→ FAMILY_MAPPING
```

JSON toàn bộ file được biểu diễn bằng immutable document manifest trỏ tới mọi
page JSON version; có thể materialize thành một document JSON khi export nhưng
không dùng một document blob làm search path chính.

Index tối thiểu phải hỗ trợ:

- document/page/source order;
- content type, statement type, note/section path;
- exact label, normalized label và token/ngram;
- ancestor/parent/sibling/previous/next signatures;
- table/row population, period, unit và scope;
- numeric value fingerprints và equation signatures;
- continuation/page-window retrieval;
- content/spec/model/prompt keyed cache.

## 7. Tiếng Việt không dấu và các search representation

Có, nên tạo tiếng Việt không dấu để tăng recall tìm kiếm, nhưng chỉ là một
projection dẫn xuất được tạo local, deterministic và versioned. Không gửi
Gemini yêu cầu tạo thêm bản không dấu và không thay thế văn bản gốc.

Mỗi label/text nên giữ song song:

1. `text_exact`: nguyên văn Gemini chép từ ảnh;
2. `text_nfc`: Unicode NFC;
3. `text_search_normalized`: case/whitespace/punctuation normalization có
   version;
4. `text_ascii_folded`: bỏ dấu tiếng Việt để candidate retrieval;
5. token/ngram index và, nếu có lợi qua benchmark, embedding search key.

`text_ascii_folded` chỉ tạo candidate. Mapping authority vẫn phải kiểm tra
`text_exact`, local graph, hierarchy, period/unit/scope, neighborhood và
accounting equations. Các từ khác nhau sau khi bỏ dấu không được tự động xem là
cùng identity.

## 8. Region-first retrieval cho từng family

Sau khi database JSON hoàn chỉnh, pipeline vẫn đi lần lượt qua từng accounting
family, không tìm/match trên toàn bộ database hoặc toàn bộ document graph trong
mỗi lần.

Cho một family spec:

1. Dùng hai schema anchors có quan hệ mạnh: parent-child hoặc sibling-sibling.
2. Query exact/normalized/accent-folded index để lấy các local regions chứa cả
   hai anchor theo đúng thứ tự và quan hệ dự kiến.
3. Region bao gồm subtree liên quan, table/note owner, page chứa hit, page trước
   và page sau có continuation hợp lệ, cùng một số row/node hàng xóm trước/sau.
4. Nếu chỉ còn một region đủ evidence, chuyển region đó sang graph matcher.
5. Nếu còn nhiều region, tăng signature lên ba anchor; tiếp tục mở rộng có giới
   hạn bằng ancestor, sibling, previous/next và neighbor-family relations.
6. Nếu vẫn không duy nhất, trả `AMBIGUOUS_CANDIDATE_REGION`; không quét/fuzzy
   toàn database trong inner loop và không chọn region gần nhất tùy ý.
7. Full-document fallback chỉ được phép khi shortlist coverage chứng minh index
   bị thiếu; fallback vẫn bị giới hạn trong đúng document.

Candidate-region cache phải keyed bằng document content root + page JSON
versions + family spec + search-normalization version. Cache tăng tốc nhưng
không tạo mapping authority.

## 9. Generic family graph mapping

Family phải là declarative specification, không phải parser/layout riêng theo
ngân hàng. Không hard-code bank, file, page, note number, ordinal, period hoặc
giá trị cụ thể.

Graph matcher phải tạo và chấm các biến thể có giới hạn dựa trên:

- owner/population và root-to-node path;
- parent, ancestor, child, sibling và cousin/related-branch relations;
- ordered siblings, previous/next và local neighbors;
- page trước/sau, table/note/section continuation;
- required, optional, alternative, source-only và nonadditive roles;
- period, unit, scope, statement side và value-axis compatibility;
- labeled/unlabeled subtotal, nested subtotal và grand total;
- exact accounting equations và complete visible population.

Search bắt đầu bằng combinations hai node. Chỉ tăng lên ba hoặc nhiều node khi
hai node không tạo một winner duy nhất. Dùng bounded k-best monotone/tree graph
matching thay vì enumerate mọi tổ hợp. Giữ winner, runner-up, score components,
unmatched source nodes và unmatched schema nodes. Thiếu margin hoặc có hard
conflict phải abstain.

Same label không phải same identity. Một mapping chỉ được accept khi local graph
và accounting population khép nhất quán; text similarity hoặc accent-folded
match không được bù cho sai parent, scope, period, unit hoặc statement.

## 10. Subtotal nhiều lớp và phương trình kế toán

Phương trình phải hoạt động trên một ordered direct frontier duy nhất:

```text
leaf rows → child subtotal
child subtotals → larger subtotal
larger subtotals/adjustments → grand total
```

Không bao giờ cộng một subtotal cùng các descendants đã cấu thành subtotal đó.
Không trộn hai alternative views hoặc hai accounting populations. Một component
được tiêu thụ đúng một lần trong một selected equation frontier.

Equation gate phải yêu cầu:

- exact visible/typed values trên mọi applicable lane;
- cùng period, unit, scope, owner và population;
- complete/exhaustive direct components;
- explicit handling của negative, discount, provision, adjustment và
  nonadditive rows;
- không có unmatched numeric node trong bounded source region;
- unique frontier hoặc nhiều frontier nhưng byte/equation-equivalent;
- no duplicate, partial, mixed-level, reordered-invalid hoặc rounding rescue.

Phương trình được dùng để:

1. kiểm tra một hierarchy/mapping do JSON graph đề xuất;
2. chọn duy nhất giữa các graph alternatives đã được source-observed;
3. suy luận ngược quan hệ parent/subtotal/child khi và chỉ khi nghiệm là duy
   nhất, exhaustive và đúng trên mọi lane.

Phương trình không được dùng để thay đổi digit Gemini đã chép, backsolve một
source value không nhìn thấy hoặc biến optional/missing role thành zero. Mọi
derived relation/value phải được đánh dấu `DERIVED`, giữ equation receipt và
không ghi đè source JSON.

## 11. Hiệu năng và vận hành

- Render/call theo page content hash; unchanged page là cache hit.
- Bounded concurrency phù hợp quota OpenRouter hiện hành; retry có backoff, idempotency
  và hard budget.
- Raw response phải được lưu trước semantic validation để debug mà không gọi
  model lại.
- Database ingest theo page shard và transaction nhỏ; index/materialized view
  được build incrementally.
- Family query chỉ hydrate candidate region và adjacent pages, không deserialize
  toàn corpus.
- Graph/equation result cache keyed bằng toàn bộ trust closure.
- Full corpus chỉ chạy sau khi prompt/contract/focused/adversarial/targeted gates
  đều pass.
- Báo cáo cold/warm latency, API concurrency, cache hit rate, input/output token,
  chi phí/page, total cost và error/retry rate.

Endpoint pilot mặc định:

```text
model: google/gemini-3.7-flash
provider: google-vertex/global/flex
fallback: disabled
data_collection: deny
structured JSON Schema: required
```

Corpus production hiện chạy OpenRouter Google Vertex Flex, stateless,
OpenRouter-only và tối đa 25–30 request hữu ích đồng thời. Các Google Batch đã
hoàn thành trước 2026-08-27 chỉ là version lịch sử/cached input; không submit
batch Google mới và không dùng Google fallback. Không đổi model/prompt/schema
trong lúc corpus đang chạy nếu chưa có equivalence panel và version mới.

## 12. Lộ trình thực hiện

### Phase 0 — Freeze và inventory

- Giữ nguyên pipeline/artifact OCR cũ để reproducibility, không phát triển thêm.
- Inventory PDF, pages, hashes, report metadata và các hard cases đã biết.

### Phase 1 — Prompt và JSON contract evaluation

- Freeze benchmark images/ground truth.
- Chạy ma trận prompt/model settings/DPI/repeats.
- Chọn prompt + response schema bằng accuracy, determinism, cost và latency.
- Sau panel trang khó, chạy pilot trọn đúng một PDF để bao phủ trong cùng một
  tài liệu: cover/mục lục, narrative, CDKT, KQKD, LCTT, notes flat/nested,
  continuation và trang không liên quan. Pilot phải có disposition cho mọi
  trang, không chỉ những trang đã biết chứa family.
- Public hóa failure ledger; chưa chạy toàn corpus.

### Phase 2 — Versioned page/document JSON store

- Xây raw/canonical/normalized/numeric/graph tables và indexes.
- Xây content-addressed cache, ingestion replay và tamper tests.
- Pilot trên một tập nhỏ gồm statement, note, continuation và irrelevant pages.

### Phase 3 — Bounded corpus ingestion

- Chạy theo document/page shards với budget và monitoring.
- Validate JSON, classification, token/cost và retry ledger.
- Chỉ sau audit pilot mới mở full corpus.

### Phase 4 — Family engine migration

- Thay OCR/geometry input của shared family algorithms bằng database JSON graph.
- Giữ family semantics declarative.
- Triển khai 2-anchor → 3-anchor region retrieval, k-best graph matching,
  multi-level subtotal/direct-frontier equations và fail-closed acceptance.
- Sau khi toàn corpus đã có page JSON, bắt đầu mapping lại tuần tự từ Family 1
  đến Family cuối cùng; không tiếp tục từ Family 12 chỉ vì đó là family đang mở
  của pipeline OCR lịch sử. Các ca khó cũ là benchmark/regression, không quyết
  định thứ tự migration mới.

### Phase 5 — Production mapping và export

- Chạy từng family trên bounded indexed regions.
- Lưu versioned candidates/mappings/equation receipts/unresolved.
- Xuất structured data/Excel với page-level provenance.
- Chạy unseen-document holdout, restore test và cost/performance audit.

## 13. Definition of done

Goal hoàn thành khi:

1. Một prompt/JSON contract Gemini 3.7 Flash qua OpenRouter Google Vertex Flex
   đã freeze sau benchmark
   đa dạng và không còn lỗi material trên certified hard panel.
2. Mọi trang trong corpus có immutable page disposition và versioned JSON hoặc
   typed unresolved, không có silent drop.
3. Database chứa raw, canonical và derived versions với indexes/replay/cache;
   unchanged runs không gọi Gemini lại.
4. CDKT, KQKD, LCTT và quantitative TM đều được biểu diễn bằng cùng page/document
   JSON contract.
5. Family retrieval chạy region-first bằng 2→3 anchors và local neighborhood,
   không full-database scan trong inner loop.
6. Family mapping tổng quát qua owner/parent/child/sibling/order/neighbor/
   continuation/period/unit/scope và không có bank/page routing.
7. Multi-level subtotal và grand-total equations dùng đúng exhaustive direct
   frontier, không mixed-level hoặc double consumption.
8. Mọi accepted mapping có source page/hash, JSON version, graph/equation
   receipt và winner/runner-up evidence; ambiguity giữ unresolved.
9. Không có PP-OCR 6, VietOCR hoặc geometry dependency trong active pipeline.
10. Accuracy, coverage, unresolved, latency, token và chi phí được báo trên
    explicit denominators; unseen-filing evaluation và restore test đều pass.

## 14. Ledger và tài liệu trạng thái của lần làm lại

Không sửa nghĩa lịch sử của `docs/experiments/COMPLETED_TM_FAMILIES.md`. File đó
tiếp tục mô tả các family đã hoàn thành bằng pipeline trước đây.

Pipeline làm lại tạo hai file trạng thái riêng:

- `docs/experiments/GEMINI_JSON_FIRST_UNRESOLVED_LEDGER.md`: các case OPEN hiện
  hành luôn ở đầu file, sau đó mới tới CLOSED/SUPERSEDED history;
- `docs/experiments/GEMINI_JSON_FIRST_FAMILY_PROGRESS.md`: tiến độ tuần tự từ
  Family 1 đến Family cuối cùng, bind page-JSON/database/prompt/model version.

Lỗi có tính tổng quát, nguyên nhân, falsifier và biện pháp phòng ngừa vẫn phải
được bổ sung vào `docs/experiments/RECURRING_FAILURE_PATTERNS.md`. Ledger mới
không được xóa hoặc viết lại bằng chứng lịch sử trong
`UNRESOLVED_MAPPING_LEDGER.md`; nếu cần tham chiếu case cũ thì dùng liên kết và
ghi rõ pipeline/version.

## 15. Non-goals và cấm triển khai

- Không hard-code theo ngân hàng, PDF, trang, note, năm hoặc expected value.
- Không dùng accent-folded text làm final identity.
- Không dùng Gemini để trực tiếp chọn ReportNormId trong bước OCR.
- Không coi JSON hợp lệ hoặc model tự tin là đủ để accept mapping.
- Không sửa source digit bằng phương trình.
- Không cộng subtotal cùng descendants hoặc bỏ unmatched numeric row để làm
  equation đóng.
- Không chạy lại Gemini cho cùng immutable input/trust closure.
- Không scan toàn database cho mỗi family khi indexed local region chưa được
  dùng.
- Không quay lại PP-OCR 6, VietOCR, geometry hoặc layout threshold khi Gemini
  JSON không đủ bằng chứng; phải retry có giới hạn, review hoặc unresolved.
