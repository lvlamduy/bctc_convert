# Read-only cross-family continuation audit

## Kết luận

Nên triển khai một primitive continuation dùng chung, nhưng chỉ sau khi shared-provenance repair hiện tại được đóng và kiểm lại. Triển khai đầu tiên phải ở chế độ shadow, không thay đổi mapping. Census đã đối chiếu 35 tài liệu terminal thuộc F16/F22/F28/F29/F30/F31/F38 và toàn bộ 21 ca `U` của F36 trên full271 authority.

Không thấy false positive trong 35 ca terminal: cả 35 cạnh đều liền nhau theo selected-page và physical-page; 34/34 sender có bảng đều là bảng MONEY cuối trang; 35/35 receiver là bảng MONEY đầu trang. Ca còn lại là F30 ordinal 254: trang sender chỉ có owner heading, không có bảng MONEY. Tuy vậy shared engine hiện không mã hoá invariant sender-last/receiver-first trong generic receipt, nên đây vẫn là một lớp false positive tiềm ẩn khi có bảng không liên quan chen giữa.

Không dùng OCR, geometry, provider hay suy đoán từ độ lớn; không sửa repo, SQLite hoặc S3.

## Authority và phạm vi

- Full271: 271 tài liệu, 14.945 selected pages.
- Manifest SHA-256: `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`.
- SQLite store SHA-256: `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.
- Cross-family code baseline: commit `3f4aa28f4b617a7adc2f6edb279a0b9c17309ccf`.
- F36 code baseline: commit `9a01a391dc097283ba436ef01e76ce56d42f4a5b`.
- Machine census đầy đủ, hashes của terminal artifacts, PDF và render nằm trong `continuation-primitive-audit-v1.json`.

## Chiến lược hiện hữu chính xác

F16 có logic riêng giàu nhất: marker hai chiều, selected/physical adjacency, parent lineage lấy từ caption bị tách hoặc group gần nhất, reset fence và giới hạn owner window; ordinal 252 còn có projection một MONEY lane hoàn toàn blank sang receiver hai lane. Ảnh PDF xác nhận đây là ngắt trang thật, không phải bảng mới.

F22 có 14 ca receiver ghi `FROM_PREVIOUS` nhưng sender thiếu `ON_NEXT`. Adapter chỉ nhận sender là MONEY table cuối trang, receiver là MONEY table đầu trang, axis kỳ/đơn vị lặp chính xác và receiver kết thúc bằng một total. Ordinal 257 là ca hai marker và receiver header blank kế thừa axis.

F28 có một ca generic hai marker/header blank (ordinal 202) và một ca one-sided family-local (259). Ordinal 259 hiện không thay hierarchy/row kind; hai danh sách normalization trong receipt đều rỗng. Tuy nhiên code có nhánh normalization tuỳ chọn mà chưa có inverse source-ref restorer tập trung; đây là rủi ro tiềm ẩn cho ca tương lai, không phải lỗi output terminal hiện tại.

F29 ordinal 248 dùng generic reciprocal continuation; receiver blank kế thừa period/unit và root được đóng bằng hợp các root-component đã khai báo.

F30 dùng ba biến thể: generic repeated-axis (58), exact leading receiver child scope từ parent ở sender (247), và owner-only heading page nối sang một receiver đầy đủ (254).

F31 ordinal 67/68 dùng projection riêng cho terminal `Cộng`: chỉ lấy prefix receiver đến total, dừng trước owner/bảng khác, kiểm equation rồi inverse-restore row locator/hierarchy/kind. Ordinal 67 đặc biệt quan trọng vì sau prefix F31, cùng table còn chứa các family 27–30. Ordinal 255 dùng generic blank-header continuation.

F38 ordinal 250/251 dùng generic blank-header continuation. Ordinal 244 là root-only receiver được xác thực bởi hai PDF source-repair receipts; không nên tổng quát hoá repair-specific rule này thành admission rule chung.

F36 có 25 family-local continuation projection receipts. Nó đã có period qualifier comparison (dates, quarter, cumulative, month duration), semantic lane bijection, parent/frontier scoping, private clone và inverse restoration cả row lẫn money-column ordinals. Ordinal 205 chứng minh thay đổi layout thật: sender MONEY `[1,2]`, receiver blank MONEY `[2,3]`. Không có terminal quan sát nào đảo ngược thứ tự lane, nên reverse-column vẫn cần synthetic test.

## F36: 21 ca U được reconcile

Mười ca nằm trên đường continuation, nhưng không được gọi là mapping mới:

- EIB 37/46/47/48/51/52: sender có `ON_NEXT`; trang liền sau có receiver `FROM_PREVIOUS`, là `s1:t1`, có đúng hai MONEY lanes và một terminal TOTAL. Receiver hiện nằm ngoài owner fence nên cluster chỉ giữ sender, sau đó root chỉ được suy ra.
- SGB 149/158/159 và STB 206: shared query đã phát hành continuation receipt hợp lệ và đã chọn cả hai trang. Chúng vẫn `U` vì terminal TOTAL bị để unbound, nên root chỉ xuất hiện dưới dạng component sum. Sửa continuation primitive một mình không giải quyết bốn ca này; cần owner-bound terminal-root binding riêng.

Chín ca 57/60/92/93/97/102/157/237/238 là bảng một trang, không phải continuation. PDF/JSON cho thấy `Cộng`/`Tổng` hoặc một terminal row được Gemini gắn `TOTAL`, nhưng evaluator không bind nó thành exact family root. Đây là workstream terminal-root binding, không được cộng vào lợi ích continuation.

Hai ca VAB 243/253 phải tiếp tục fail-closed. Chúng có unlabeled terminal total và blank provision row; 243 còn không có local unit usable trong tài liệu có cả VND và triệu đồng. Không được dùng equation hoặc độ lớn để tự chọn unit/owner.

## False-positive và false-negative audit

False negative thực tế đáng ưu tiên là F36: sáu EIB bị đứt owner fence, bốn SGB/STB đã nối trang nhưng không bind root, và chín bảng tự-contained không bind generic terminal total. Các nhóm này phải tách thành hai primitives: origin-bound continuation và owner-bound terminal-root.

Generic shared receipt hiện kiểm hai loại adjacency, marker hai chiều, period axis, blank-axis inheritance, role lineage và uniqueness của predecessor. Nó chưa buộc sender là last relevant MONEY table, receiver là first relevant MONEY table; chưa quét một cách content-addressed toàn bộ sender suffix/receiver prefix; và chưa truyền một `origin_id` bất biến đến mọi fragment/source_ref. Vì vậy các tình huống bảng không liên quan chen giữa, cùng label dưới owner khác, hoặc reset ở prefix/suffix phải có veto tường minh.

Family-local logic có nhiều bảo vệ mà primitive chung phải giữ: F22 last/first table; F31 row-frontier trong cùng table; F16 group-parent lineage; F36 semantic period qualifiers và inverse column restoration. Không nên thay tất cả bằng một phép “ghép trang” đơn giản.

## Source provenance

Đối chiếu trực tiếp source refs với `row_node` của SQLite cho toàn bộ ca terminal F22/F28/F29/F30/F31 và 25 positive-projection docs của F36 cho 0 mismatch ở `row_id`, ordinal, label, hierarchy và row kind. F31/F36 inverse restoration đang làm đúng.

Các terminal artifacts cũ vẫn chứa exact duplicate refs: F22 122/244, F28 26/52, F29 5/11, F30 34/68, F31 26/53; F16 6/135. F38 0/9 và 25 F36 positive docs 0/299. Đây là lý do phải hoàn tất shared-provenance repair trước khi thêm primitive mới.

## Thiết kế `origin_bound_continuation_v1`

Primitive nên là pure classifier phát hành `ACCEPTED`, `REJECTED(reason[])` hoặc `NOT_APPLICABLE`; tuyệt đối không sửa source authority. Receipt cần bind:

1. `origin_id` băm từ document/source SHA, exact owner locator/surface, reset fence và immutable table snapshots.
2. Sender/receiver locators, selected + physical adjacency, sender-last/receiver-first relevant MONEY topology; owner-only và receiver-prefix là variant có policy riêng.
3. Marker policy: reciprocal mặc định. One-sided chỉ bật theo family policy, receiver phải explicit và có exact origin/parent anchor.
4. Period/lane bijection, qualifiers và explicit unit evidence. Blank receiver chỉ kế thừa từ đúng predecessor; explicit conflict luôn veto.
5. Row frontier và lineage: parent/child/neighbour order, prefix end/reset row, split-label/value fragments, cùng label nhưng khác owner bị loại.
6. Chain identity: predecessor receipt, monotonic multi-page order, không fork/cycle, giới hạn page budget.
7. Original source snapshot và inverse map. Evaluation chạy trên private clone; trước khi phát hành mapping phải restore locator/row/column, reseal IDs và cấm exact duplicate refs.

Arithmetic chỉ dùng làm hậu kiểm sau admission, không dùng để chọn bảng, owner, kỳ, unit hoặc điền blank/zero.

## Test matrix bắt buộc

Positive: reciprocal repeated header; reciprocal blank receiver; family-gated one-sided; semantic reordered/shifted columns; split label; split label/value; three-page chain; owner-only heading; receiver-prefix rồi reset trong cùng table; repeated running header cùng origin; terminal total closure sau admission; exact source-ref inverse restoration.

Negative: selected-only hoặc physical-only adjacency; unrelated MONEY table chen giữa; reset trong sender suffix/receiver prefix; same label/different owner; explicit unit conflict; missing/ambiguous unit; reversed/conflicting period roles; duplicate/non-bijective lane; blank receiver không marker; one-sided không family gate; hai predecessor/receiver; fork/cycle/over-budget chain; disjoint lineage; arithmetic đúng nhưng owner sai; blank bị dùng như zero; row reorder vượt parent frontier; source-ref chưa restore/trùng; snapshot/receipt bị sửa; repair-only case thiếu authenticated repair.

## Trình tự triển khai

1. Đóng shared-provenance repair và rerun terminal gates.
2. Thêm primitive ở shadow mode; không thay output. Chạy parity theo thứ tự F22 → F28 → F29 → F30 → F31 → F38 → F36.
3. Giữ F38 repair-specific admission ngoài generic core; primitive chỉ tiêu thụ authenticated source view.
4. Đưa F36 period-alignment và inverse-restoration semantics thành callback/helper dùng chung.
5. Chỉ đưa F16 vào sau khi shadow parity chứng minh không mất multi-role parent lineage và blank-stub behavior.
6. Làm terminal-root primitive riêng cho 13 ca F36 liên quan root; không gộp nó vào continuation.

