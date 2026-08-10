# Brief — critical path từ V3 sang corpus survey

Updated: 2026-08-10T23:26:43+07:00

## Kết luận đối chiếu chiến thuật

Chiến thuật hiện tại vẫn đúng hướng breadth-first: MBB là development baseline đã niêm phong, VPB là regression evidence, còn Wave 1 là một BCTC đại diện của đủ 27 ngân hàng. V3 chỉ là bước hoàn tất denominator bằng chứng trang trung lập trước khi khảo sát cấu trúc; nó không phải KPI cuối và không được kéo dài thành một dự án OCR riêng.

## A. Đang làm chính xác bước nào?

Full-reader V3 đã được freeze, commit và push tại `4e51dc5ad50a0a9597f9d867f3de5ed94716b64c`. Control production đã được xuất bản và replay độc lập thành công:

- control identity: `abec67c1e15f5cc2bc7be08abe58652eda6f855879ea7a72afce2dbcee52ac36`;
- artifact SHA-256: `4d8e3206e6518c2e61104aa9cda6bcea310211fa2e5bec39c38b919abe4536e8`;
- accounting plan: 27 documents, 1,449 requests, 1,356 OCR adoptions, 93 fresh native reads, 4,068 OCR object copies và 4,254 final objects;
- hiện chưa có V3 checkpoint, document index hoặc aggregate; chỉ có control và execution lease hợp lệ.

Ngay lúc này bước kế tiếp đã `GREEN TO RUN`: copy/rebind 1,356 OCR authorities từ archive V2 vào V3 và thực hiện mới toàn bộ 93 native requests. Không chạy OCR inference mới.

## B. Bước này phục vụ PDF → cấu trúc → khoản mục → số liệu → Excel thế nào?

Đây là điều kiện đầu vào trực tiếp cho structural survey, nhưng chưa phải structural survey. Nó tạo một denominator page-evidence thống nhất cho đủ 1,449 trang:

```text
PDF bytes đã xác thực
→ text/word/line/geometry evidence hoặc explicit terminal disposition
→ page checkpoints và document indexes bất biến
→ nguồn đầu vào trung lập cho statement/table/row/cell survey
```

Nhờ vậy tầng sau có thể đo coverage thật thay vì nhầm trang thiếu dữ liệu với trang trống, và có thể giữ `UNRESOLVED` thay vì bịa table/row/cell. V3 cố ý không dùng bank metadata, filename, Role A, schema, mapping hoặc historical values để quyết định đọc trang; các interpretation counters đều bằng 0.

## C. Có over-engineer reader/GREEN/S3/audit không?

Có, giai đoạn vừa qua đã dùng tỷ trọng thời gian lớn cho recovery, TOCTOU, crash-state và audit so với tiến bộ trực tiếp về statement/table/row/cell. Phần đó từng cần thiết vì V1/V2 đã có lỗi publication và native ordering thực, nhưng ngưỡng an toàn cần thiết nay đã đạt.

Từ đây dừng các việc sau nếu không xuất hiện lỗi cụ thể:

- không tạo V4 chỉ để làm mọi trang complete;
- không thêm recovery/version/audit mới sau khi V3 run, verify, finalize và resume gate hoàn tất;
- không lặp lại full-1,359 replay nếu byte/contract không đổi;
- không mở rộng kiến trúc S3; chỉ tạo một checkpoint V3 có manifest, checksum và restore test;
- không benchmark thêm OCR/VLM nếu chưa có failure class downstream đo được.

Các bước còn lại của V3 — run, verify/finalize, zero-new-native resume và một backup restore-tested — là đóng milestone hiện tại, không phải mở rộng hạ tầng.

## D. Năm bước thực thi tiếp theo

1. Chạy V3: adopt đủ 1,356 OCR page records và thực hiện mới 93 native requests; mỗi request phải có đúng một disposition đóng.
2. Verify, finalize aggregate 1,449 requests, chạy completed resume với 0 native build/deep replay/render mới và 0 output mutation; sau đó freeze reader.
3. Tạo đúng một S3 checkpoint cho V3 đã hoàn tất, kiểm tra remote checksum và full/sample restore; cập nhật status rồi dừng nhánh reader/infrastructure.
4. Chạy Role-B source-first survey trên cả 27 BCTC: page-local proposals rồi content-addressed document graphs cho `PAGE → STATEMENT_BLOCK → TABLE → ROW → CELL → AXIS → EVIDENCE`; seal Role B trước khi so với Role A.
5. So sánh riêng với 139 Role-A statement blocks, gom archetypes/failure classes, sửa generic algorithms và replay corpus; sau đó mới canonicalize schema, bind period/unit/scope, validate accounting và xuất mapped Excel.

## E. Khi nào bắt đầu survey 27 ngân hàng?

Ngay sau khi V3 có aggregate đã verify/finalize, completed-resume gate đạt và checkpoint S3 duy nhất được restore-test. Không chờ mọi terminal page trở thành complete, không chờ line supplement hoàn hảo và không mở một vòng reader tuning mới. Đây là critical-path stage kế tiếp, không phải công việc “sau này”.

## F. Kế hoạch mở rộng sau Wave 1

Không brute-force 2,435 PDF unique. Mỗi wave được chọn trước khi đọc nội dung bằng điểm information gain trên các trục chưa phủ, đồng thời phạt duplicate content và strata đã đủ mẫu.

- **Wave 2 — temporal stability:** tối đa một tài liệu khác kỳ cho mỗi ngân hàng, ưu tiên Q1, Q3 hoặc năm và giữ các trục khác gần Wave 1 để cô lập biến đổi theo thời gian.
- **Wave 3 — scope/report-form pairs:** chọn các cặp hợp nhất/riêng lẻ và quý/bán niên/năm ở nơi registry có đủ cặp, ưu tiên cùng ngân hàng và gần kỳ để cô lập scope/report type.
- **Wave 4 — assurance/source-route coverage:** bổ sung kiểm toán/soát xét/chưa kiểm toán và scan/native/mixed, ưu tiên archetype hoặc failure class chưa được giải thích.
- **Các wave sau:** lấy residuals có uncertainty hoặc expected information gain cao nhất; giữ một tập bank-disjoint và period-disjoint chưa mở cho đánh giá cuối.

Mỗi wave lặp đúng chu trình: survey → archetype/failure registry → generic fix → replay → schema convergence → mapped Excel → chọn strata tiếp theo.

## G. Kiểm soát UNIVERSAL_SCHEMA không tăng vô hạn

Quy tắc quyết định:

- cùng bản chất kế toán, khác cách gọi ngân hàng/ngôn ngữ viết tắt → cùng canonical ID và thêm alias;
- khác note, page, thứ tự, indentation hoặc layout → presentation difference, không tạo ID;
- heading, dimension, unit, period header và row chỉ phục vụ trình bày → không tạo accounting identity;
- chỉ đề xuất ID mới khi source evidence chứng minh khác measure/accounting meaning/role/parent context và không biểu diễn đúng bằng ID, alias hoặc dimension hiện có;
- trường hợp một tài liệu chưa đủ phân biệt → `UNRESOLVED_SCHEMA_GAP`, không tự động append;
- canonical ID là append-only; ID có vẻ trùng nghĩa được đưa vào canonicalization/deprecation review với alias/migration rõ ràng, không âm thầm tái sử dụng.

KPI bắt buộc theo từng wave, cả số tuyệt đối và trên 1,000 source rows:

- genuine new IDs;
- aliases;
- presentation-only differences;
- unresolved schema gaps;
- duplicate/canonicalization candidates;
- tỷ lệ alias:new-ID;
- new-ID rate và rolling trend qua ít nhất hai wave.

Nếu new-ID rate không giảm qua hai wave liên tiếp, hoặc new IDs tăng nhanh hơn aliases mà không có archetype kế toán mới, tạm dừng mở rộng schema và audit lại normalization/canonicalization trước khi append thêm.

## H. Có hard-code theo MBB/VPB/bank/note/kỳ không?

Có code lịch sử mang tên MBB và VPB trong `config/experiments`, scripts calibration, fixtures và tests; đó là sealed development/regression surface và không được dùng làm production selector.

Kiểm tra trực tiếp ba production V3 files và policy hiện tại cho thấy:

- không có tên MBB, VPB hoặc bank cụ thể;
- không có ngày/kỳ báo cáo hay note number dùng làm nhánh quyết định;
- không có ReportNormId hoặc mapping/schema input trong page reader;
- policy bắt buộc `bank_registry_metadata`, filename, Role A, schema, mapping và historical values đều không được dùng.

Hai ràng buộc có chủ đích là Wave-1-specific: exact sealed 27-document plan/counts và exact failed-V2 archive hashes. Đây là versioned authority binding, không phải logic suy luận theo ngân hàng. Native V2 test có real VPB page-2 regression gate, nhưng adapter production không có nhánh VPB. Rủi ro cần tiếp tục chặn là tầng structural survey mới vô tình import các MBB calibration defaults hoặc VPB answers; import/input-ledger tests phải giữ các surface đó ngoài production.

## I. Stop rule nếu V3 còn terminal-unresolved

Vẫn tiếp tục structural survey khi mọi request có đúng một disposition đóng, kể cả explicit terminal. Reader được freeze nếu đồng thời:

1. đủ 1,449 checkpoints và 27 indexes;
2. không có missing/foreign/unreferenced object;
3. verify/finalize deterministic pass;
4. completed resume không tạo native evidence mới và không sửa output;
5. terminal pages giữ nguyên provenance và không bị relabel thành blank/complete.

Không sửa reader chỉ vì còn 57 OCR geometry-terminal pages hoặc có thêm native terminal pages. Chỉ mở lại reader khi survey chứng minh cùng một failure class:

- làm mất toàn bộ một main-statement block; **hoặc**
- ảnh hưởng ít nhất 2 ngân hàng; **hoặc**
- ảnh hưởng ít nhất 3 statement/table blocks; **hoặc**
- ảnh hưởng ít nhất 1% denominator logical rows/value positions đã quan sát.

Khi đó sửa bounded mechanism và replay đúng tập trang bị ảnh hưởng; không mặc định tạo V4 cho toàn corpus. Các lỗi đơn lẻ dưới ngưỡng vẫn là `UNRESOLVED` và không chặn breadth-first survey.

## KPI chuyển pha ngay sau V3

KPI chính không còn là số audit hay reader tests mà là:

- Role B tìm được bao nhiêu trên 139 Role-A statement blocks;
- tables, logical rows, cells/value positions và source objects accounted;
- số structural archetypes và số ngân hàng/tables/rows mỗi archetype bao phủ;
- failure-class prevalence và corpus coverage của từng generic fix;
- aliases, genuine new IDs, presentation differences và unresolved gaps;
- số ngân hàng tạo được mapped Excel và delta sau mỗi corpus replay.
