# Hướng dẫn Claude triển khai ba bảng báo cáo tài chính

Đọc toàn bộ [mục tiêu](CLAUDE_PRIMARY_STATEMENTS_GOAL_2026-10-21.md) và hướng dẫn này trước khi sửa code. Claude phụ trách CDKT, KQKD và LCTT; Codex tiếp tục TM. Làm việc tự chủ, ưu tiên đi từ dữ liệu đã có đến Excel có kiểm chứng, và dừng an toàn ở đúng gate khi thiếu bằng chứng.

## Đọc authority và chốt base

Đọc đầy đủ:

1. `AGENTS.md`.
2. `docs/operations/MACHINE_MIGRATION_CHECKPOINT_2026-09-05.md`.
3. `PROJECT_OPERATING_DIRECTIVE.md`.
4. `docs/GEMINI_JSON_FIRST_PROJECT_GOAL.md`.
5. `docs/experiments/GEMINI_JSON_FIRST_USER_REQUIREMENTS.md`.
6. `docs/operations/MACHINE_MIGRATION_F37_PIN_CORRECTION_2026-10-03.json` và checkpoint/correction liên quan.
7. `docs/contracts/universal_bank_bctc_schema.md`, registry, coverage và các hợp đồng đầu vào sẽ sử dụng.

Repo authority: `https://github.com/lvlamduy/bctc_convert.git`. Migration base là `8efd618b6c77f0cdbb402a440e7ba3b3549184f1`. Không dùng checkout `main` cũ hoặc `codex/rebuild-bootstrap`.

Base triển khai PRIMARY là **commit đã push tạo hai file bàn giao này**, trên nhánh `codex/f39-income-tax-laptop`, chứa checkpoint `F39_RECOGNITION_AND_RATE_EFFECT_CHECKPOINT_2026-10-21.md`. Lấy SHA đầy đủ từ bàn giao/event của Codex và đối chiếu Git; không bắt đầu từ một HEAD chưa commit. Nếu cần tìm commit tạo file, dùng lệnh chỉ đọc sau sau khi fetch đúng nhánh:

```powershell
git -C D:\bctc_bank\bctc-ai-2025-current log origin/codex/f39-income-tax-laptop --diff-filter=A --max-count=1 --format=%H -- docs/operations/CLAUDE_PRIMARY_STATEMENTS_GOAL_2026-10-21.md
```

Ghi chính SHA 40 ký tự đó vào preflight/run manifest. Xác minh migration base là ancestor, HEAD worktree mới đúng base, Git status sạch và các pin nguồn khớp. Không tự thay base giữa một run.

Các đoạn lịch sử trong repo nói về PPOCR/VietOCR/geometry hoặc ingestion trả phí không cấp quyền dùng lại các tuyến đó. Phân công mới này chỉ mở phạm vi ba bảng PRIMARY song song, không mở family TM mới.

Phần TM của Codex vẫn theo thứ tự F39 rồi F36 rồi F37; F41 chưa được mở trước khi cả ba terminal. Nhiệm vụ PRIMARY độc lập của Claude không đổi thứ tự đó.

## Worktree và quyền sửa

Tạo worktree riêng, đề nghị `D:\bctc_bank\bctc-primary-claude`, branch `codex/primary-statements-claude`, từ base đã xác minh. Kiểm tra đường dẫn/branch chưa được người khác sử dụng; nếu đã tồn tại thì kiểm tra và tiếp quản có bằng chứng, không xóa hoặc ghi đè. Không checkout hoặc đổi branch trong worktree đang chạy F39 của Codex.

Mã mới nên nằm trong namespace riêng:

- `src/bctc_ai/primary_statements/`.
- `config/primary_statements/`.
- `scripts/primary_statements/`.
- `tests/unit/test_primary_statements_*.py` và các fixture riêng.
- `docs/operations/primary-statements/` cho kế hoạch, benchmark và ledger.

Chỉ tạo/sửa các vùng PRIMARY đã claim. Không sửa `config/families/tm-*`, evaluator/runner/test F39 hoặc family TM khác, `AGENTS.md`, authority documents, schema/template dùng chung, source loader/store dùng chung hay exporter cũ khi chưa có review riêng. Schema gap hoặc primitive dùng chung cần mở rộng phải được ghi rõ cho Codex, không âm thầm đổi contract.

Hai file sau frozen, chỉ đọc và kiểm SHA trước/sau:

| File | SHA256 |
| --- | --- |
| `src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py` | `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2` |
| `scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py` | `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5` |

## Runtime và dữ liệu đã phục hồi

Laptop đã có môi trường WSL và Python 3.12 hoạt động; không tự cài lại WSL/Ubuntu. Runtime đã kiểm chứng:

```text
WSL distribution: BCTC-Ubuntu-24.04
Python: /srv/bctc-runtime/venv/bin/python
Artifact root full271:
/srv/bctc-restore/dev-shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts
PDF root Windows: D:\bctc_bank\restore-20260905T014806Z\source
PDF root WSL: /mnt/d/bctc_bank/restore-20260905T014806Z/source
```

Dùng Python 3.12 với `-B`, import từ **worktree Claude**, prefix bytecode/output mới ngoài repo và tắt pytest cache. Không dùng Python 3.14. Miniconda có trên laptop nhưng không mặc định mọi environment đều có pytest; không cài lại dependency chỉ vì chọn nhầm môi trường. Khi chạy từ Windows, có thể dùng `wsl -d BCTC-Ubuntu-24.04 -- /srv/bctc-runtime/venv/bin/python -B ...` với cwd và đường dẫn đã kiểm chứng.

Full271:

- Index tương đối dưới artifact root: `current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`.
- SHA index: `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`.
- DB: `current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`.
- SHA DB: `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`; 573.145.088 byte.

Common204 độc lập:

- Root: `/srv/bctc-restore/dev-shm/bctc-ai-27-bank-family-live-v1`.
- Index: `current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`.
- SHA index: `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`.
- DB: `current-corpus-freeze-inputs/store-a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220.sqlite3`.
- SHA DB: `a14904a492e6beae165b81f7aa1738352a9824e113f1b163a46ee277d37e0220`; 553.984.000 byte.

Đây là paths runtime trên SSD; không sửa immutable manifest để thay các paths `/dev/shm` lịch sử. Mở source DB chỉ đọc. Mỗi run ghi database kết quả riêng, không ghi cạnh hoặc sửa DB nguồn; không thay selected JSON versions, PDF, raw payload hoặc CAS objects.

PDF inventory đã pin: `/srv/bctc-receipts/pdf-inventory-v2/SOURCE_PDF_BYTE_PAGE_INVENTORY_2026-09-05.json`, SHA `f8f619280c712c872599730958012f56a115a6ea328f268c587ac6120493fc15`. Kiểm coverage/byte/page identities theo đúng production selection; inventory lưu trữ có thể chứa PDF 2024 nhưng không cấp quyền đưa chúng vào production.

Restore authority là bucket `test-s3-duylv`, region `us-east-1`, manifest key `bctc-ai/machine-migrations/20260905T014806Z-family40-checkpoint/manifest/migration-manifest-final.json`, SHA `2376cb2cbebdbe8d55f18679ee0982b7ee77a9bf610a5d214b75d32fe8bb6312`, VersionId `0_OPgrF.1VhQ9unZoVC4fyuNV2a0GF4a`. Tái sử dụng receipt restore PASS đúng corpus và kiểm lại các đầu vào thực tế; không tải lại toàn bộ khi dữ liệu đã đủ. Nếu cần restore object thì dùng exact VersionId, kiểm byte count và SHA trước giải nén. Thiếu PDF/database/object là lỗi restore, không phải quyền re-extract.

## Preflight trước mutation

Báo PASS hoặc FAIL riêng cho Git/base/worktree, runtime/import origin, schema/template pins, corpus/index/source DB, PDF coverage và byte identities, SQLite `quick_check`/`foreign_key_check`, frozen hashes, coordination claim và không có provider job. Chạy bằng chứng kiểm tra, không sao chép chữ PASS từ một báo cáo cũ có đầu vào khác.

Kiểm AWS identity và bucket versioning trước thao tác S3. Nếu AWS chưa được cấu hình thì dừng và chỉ yêu cầu người dùng đăng nhập AWS; không suy đoán credential. Không đọc, in, commit hoặc upload `openrouter_api.txt`, `D:\bctc_bank\codex-session.passphrase`, hay secrets khác. Không cần GPG cho nhiệm vụ PRIMARY này.

Không gọi Gemini, OpenRouter, Vertex, Agy hoặc provider nào; không tạo job OCR/ingestion/retry. Không phục hồi hoặc sử dụng PPOCR6, PaddleOCR, VietOCR, geometry OCR, DeepSeek/DeepSeak OCR hay Gemma. Có thể kiểm tra PDF bằng render để xác thực một vùng cần review; đó không phải quyền OCR lại hoặc ghi đè JSON. Bất kỳ correction nào cũng cần nguồn, before/after, hash và quy trình đăng ký riêng.

## Bản đồ code nên đọc và tái sử dụng

| Thành phần | Đường dẫn dưới `src/bctc_ai/` | Cách dùng |
| --- | --- | --- |
| JSON nguồn và statement types | `evaluation/gemini_financial_page_json_v1.py` | Kiểm schema/cấu trúc JSON; metadata là gợi ý truy hồi, không tự là bằng chứng phân loại đúng |
| Đọc original JSON có xác thực | `storage/gemini_income_tax_source_page_loader_v1.py` | API read-only kiểm raw JSON, SHA/CAS/provenance; tên F39 không cấp quyền sửa loader |
| Chọn đúng corpus và versions | `storage/gemini_current_corpus_manifest_index_v1.py`, `storage/gemini_current_document_manifest_selection_v1.py`, `storage/gemini_family_effective_page_frontier_v1.py` | Không lấy JSON rời, version mới nhất tiện tay hoặc dữ liệu ngoài selection |
| Trạng thái ô nguồn | `evaluation/source_observation_mapping_contract_v1.py` | Kiểm giữ nguyên quan sát; recursive audit không phải danh sách được xuất |
| Lưu và đọc lại kết quả | `storage/gemini_accounting_family_store_v1.py` | Tham khảo ingest/load/replay; validator có ràng buộc family, không ép PRIMARY mới vào format giả |
| Schema | `schema/registry.py`, `schema/coverage.py` | Đọc authority từ `config/schemas/sources.yaml`; giữ đúng ID, hierarchy, order và consumer coverage |
| Excel deterministic | `export/canonical_xlsx.py` | Tái sử dụng literal-cell handling và canonical bytes; không tự cấp acceptance |

Các template hiện hành là `template/Bank_CDKT_ReportNormId.v2.xlsx`, `Bank_KQKD_ReportNormId.v2.xlsx`, `Bank_LCTT_ReportNormId.v2.xlsx`. Xác minh bằng registry, không đổi thứ tự hay chỉ dùng các workbook BASE cũ.

Không dùng `source_structure/semantic_statement_context_v1.py`, `document_statement_hypotheses_v1.py` hoặc các exporter `cdkt_development.py`, `kqkd_development.py`, `lctt_development.py` làm engine Gemini production: chúng có phụ thuộc OCR/word-box hoặc ví dụ lịch sử. Chưa có sẵn một pipeline Gemini hoàn chỉnh cho toàn bộ ba bảng; không báo rằng chỉ cần gọi một exporter cũ là đã hoàn thành.

## Thuật toán phải xây dựng

1. Tạo census các trang và bảng PRIMARY trong selection. Xác thực loại bảng bằng caption, header, context và nội dung nguồn. Ghép continuation chỉ khi chứng minh cùng tài liệu, statement, scope và axes; giữ toàn bộ trang/hàng được sở hữu.
2. Xây hàng logic và các cột giá trị, giữ raw label, hierarchy, row kind, raw text, ordinal và source identity. Mã dòng, số tham chiếu TM và năm không tự là cha kế toán. Không bỏ numeric/Roman ancestry chỉ vì phương trình sẽ đúng sau khi bỏ.
3. Xác thực scope riêng/hợp nhất và entity, đơn vị và từng kỳ từ nguồn. Không đoán từ tên file, mã ngân hàng, vị trí trang hoặc giá trị giống nhau. Mâu thuẫn nguồn phải là veto, không chọn đa số.
4. CDKT dùng thời điểm số dư; KQKD và LCTT dùng kỳ phát sinh. Tách quý với lũy kế, current với comparative và các ngày/khoảng thời gian. Báo cáo quý không đồng nghĩa LCTT là số riêng quý. Không tự lấy năm hiện hành trừ một cho `Kỳ trước` khi chưa có chứng cứ.
5. LCTT xác thực nhánh trực tiếp hoặc gián tiếp theo nguồn và `config/mapping/lctt-v2.yaml`. Không trộn hai nhánh, không đòi quan sát cả hai nhánh trong một báo cáo.
6. Ánh xạ theo ý nghĩa, cấu trúc và accounting role vào đúng statement/schema. Alias chỉ giúp tìm ứng viên; cùng chữ không đủ chọn ID. Ghi rõ schema gap, ambiguity và nguồn bị rơi, không force-map.
7. Kiểm phương trình từ các số **đã quan sát**. Không giải ngược ô thiếu; không thay dấu/đơn vị để đóng tổng. Tổng cha và con không được cộng trùng. Cross-statement checks phải cùng entity, scope, kỳ và đơn vị; chênh lệch cần điều tra chứ không dùng để sửa số nguồn.
8. Lưu accepted result và receipts, đọc lại từ SQLite, dựng lại độc lập từ selected original JSON và so sánh exact typed results. Cache chỉ tăng tốc, không là authority.

Tối ưu bằng batch read, indexed retrieval, reuse nguyên bản có chứng thực và invalidation theo dependency. Đo số request/SQL, rows/bytes đọc, cache hits và thời gian từng stage. Chỉ cache theo source/selection/spec/code hashes đầy đủ; test cả cold run và stale/cross-version cache rejection.

## Contract kết quả và Excel

Một giá trị được chấp nhận phải truy được về document/source PDF hash, selected page/version, page/section/table/row/column, raw text, trạng thái ô, unit, kỳ, entity/scope, ReportNormId, spec/code pins, validation và mapping receipts. Source-only/structural/ambiguous rows cũng phải có disposition rõ.

`READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY` và nhãn run `OFFICIAL` tự chúng không phải acceptance hoặc quyền xuất dữ liệu production. Phải có gate chấp nhận PRIMARY với bằng chứng nguồn và kiểm chứng độc lập tương ứng.

Phân biệt printed numeric zero, `DASH_ZERO` được xác thực, `DASH`, blank, absent, unresolved và derived. `DASH` chưa có nghĩa số vẫn không là 0. Không xuất derived value như quan sát trực tiếp; nếu hỗ trợ aggregate phải có loại riêng và phương trình đầy đủ, không dùng để điền một ô nguồn bị thiếu.

Chỉ lấy **final selected accepted mappings** thuộc CDKT/KQKD/LCTT để xuất. Không duyệt đệ quy toàn bộ closure để lấy mọi object có ReportNormId: nested/private/suppressed mappings là bằng chứng, không phải dữ liệu được xuất. Không lấy TM RNIDs hoặc kết quả của Codex để lấp bảng PRIMARY.

`PipelineRecord` và `export/workbook.py` hiện có contract legacy; không giả geometry hoặc đổi nhãn sang MEDIUM để lách gate. Tạo contract/adapter receipt-aware riêng trong namespace PRIMARY, có validate từ nguồn đã được chấp nhận. Có thể dùng serializer an toàn nhưng không coi verifier layout cũ là verifier số liệu.

Khóa ghi phải phân biệt document, entity/scope, statement, period và ReportNormId. Từ chối duplicate/conflict dù hai giá trị bằng nhau; không first-wins/last-wins hoặc dùng đơn vị như khóa phụ để che trùng. Schema row order lấy từ registry/DisplayOrder, không sắp theo số ID.

Workbook ba bảng có thể phát hành độc lập dưới nhãn PRIMARY_ONLY. Giữ đúng các hàng template, trạng thái hàng không áp dụng/không quan sát được và provenance; không gán NOT_OBSERVED cho dữ liệu chưa đánh giá. Sau ghi phải mở lại và so exact cell values/types, dấu, unit, period, row order, formula allowlist và provenance/receipt links. Chặn formula injection; không âm thầm dùng float làm mất chính xác số lớn. Nếu Excel không biểu diễn chính xác được thì dùng chính sách exact-text đã được duyệt hoặc HOLD, không tự làm tròn.

## Chia việc song song và nghiệm thu

Có thể giao ba subagent riêng cho CDKT, KQKD và LCTT. Claude làm integrator cho loader/contract/export chung; mỗi agent chỉ sửa file đã phân công. Dữ liệu nguồn chỉ đọc, mỗi job ghi output/database riêng. Phối hợp tài nguyên với Codex; không chạy đồng thời nhiều full-corpus job nặng trên laptop. Không mutation code/tests trong lúc một focused/cold witness đang chụp đúng worktree đó.

Làm một lát cắt từ nguồn đến Excel có kiểm chứng trước, rồi tăng panel đa ngân hàng/kỳ/layout. Chạy focused tests trước corpus replay. Sau đó chạy full271 và common204 độc lập, không dùng panel nhỏ làm bằng chứng nghiệm thu toàn corpus. Kiểm đủ trang/hàng/ô PRIMARY, accounting/observation contracts, source replay, SQLite persist/reload/integrity và PDF/residual audit theo đúng nguồn. Không đổi UNKNOWN/ALGORITHM_HOLD thành NOT_OBSERVED để đạt tỷ lệ.

Tối thiểu phải có negative tests cho wrong statement/scope/period/unit, quarter-YTD mix, direct-indirect mix, missing/duplicate continuation, numeric-code ancestry, blank/dash, precision, duplicate target, stale selection/cache, source/config/receipt bị sửa rồi tự tính hash lại, và workbook khác giá trị/provenance sau ghi.

## Coordination và bàn giao

Trước mutation đọc các event tại `s3://test-s3-duylv/bctc-ai/coordination/2025-current/v1/events/`. Claim chỉ phạm vi `PRIMARY_STATEMENTS` với worker Claude, không claim F39 hoặc TM. Phát JSON bất biến `CLAIMED`, `HEARTBEAT`, `BLOCKED`, `READY_FOR_INTEGRATION` theo contract coordination hiện hành; chỉ phát READY khi các gate đúng phạm vi PRIMARY đã đạt. Nếu cần mở rộng schema coordination cho namespace mới thì thống nhất với Codex trước, không giả family ID.

Không dùng nguyên helper `coordination_heartbeat.py` của F39 cho claim PRIMARY vì helper đó đóng đinh worker/family khác. Mọi S3 write dùng key mới, điều kiện không ghi đè, checksum và exact VersionId readback. Không thay hoặc xóa manifest, event, artifact cũ. Không tự dọn artifacts trước khi seal đúng phạm vi.

Commit và push **chỉ branch Claude**. Không push `codex/27-bank-2025-current` hoặc `codex/f39-income-tax-laptop`. Codex review diff, focused regression và source proofs trước khi cherry-pick; Claude không tự tích hợp vào worktree Codex.

Bàn giao gồm commit/base, allowed-path diff, schema/input/code hashes, test counts và receipts, full271/common204 coverage cùng residuals, SQLite/PDF/source replay gates, workbook + provenance + exact readback receipt, benchmark và immutable artifact keys/VersionIds. Ghi rõ cái gì đã nghiệm thu, cái gì còn HOLD và bước tiếp theo. Không báo hoàn thành chỉ vì code chạy được, tạo được Excel hoặc số test xanh tăng.
