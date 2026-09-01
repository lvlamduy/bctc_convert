# Gemini JSON-first unresolved ledger

Ledger này chỉ dành cho pipeline Gemini JSON-first. Case đang `OPEN` phải luôn
được đặt trước các phần `CLOSED` và `SUPERSEDED`. Không dùng file này để sửa
lại trạng thái lịch sử của pipeline PP-OCR/VietOCR/geometry.

## OPEN — current

Không còn case OPEN tại checkpoint này; mọi provider/semantic failure vẫn chỉ
được chuyển xuống đây sau khi có receipt đóng đầy đủ document.

## CLOSED — current

- **GJF-CLOSED-020:** supervisor OpenRouter-only từng trả `NEEDS_RETRY` sau
  attempt đầu của VPB 2026 hợp nhất 91 trang nhưng giữ đúng bốn chunk ở
  `RUNNING` dưới cùng một claim. Bộ chọn document cũ chỉ nhìn
  `PENDING/NEEDS_RETRY`, nên process kế tiếp bỏ qua claim đang chạy và cần can
  thiệp tay. Commit `2c4a135a9dd00bd16c36ba9b2756953f42c4abc0` bổ sung đúng
  frontier crash-resume `RUNNING|SUCCEEDED`, tự chạy attempt kế tiếp trong giới
  hạn và không tính retry như một document mới. Actual resume chỉ tìm thiếu
  p72/p74; p74 đóng bằng `simple`, p72 provider/semantic-fail được chuyển sang
  `items`, còn 89 trang cache hit. Document kết thúc 91/91 trang với manifest
  `gfdmv1:manifest:a32077d4d84c72f1b4454d2b79aeb2cda680390c7b7e07db83b1dd793f988063`
  và selection
  `gjfcdmsv1:selection:34c462768328acb5dcd73affc6f160dd1a41b6b7901621126055d9104a41f645`;
  mọi child đều có `google-standard-mode=disabled`. Cùng checkpoint thêm
  corpus-freeze/index fail-closed; toàn bộ panel Gemini `192 passed`.

- **GJF-CLOSED-012 (trước đây GJF-OPEN-012):** Google Files API từng trả HTTP
  429 tại upload-start task p1–30 của HDB quý 2/2025 công ty mẹ. Document sau
  đó đã được phục hồi hoàn chỉnh theo `GJF-CLOSED-015`; đúng task
  `gjfptaskv1:1f6dd08d08ac1fb44321bf8ac60ce54974e47f42623905966a0aed576f1703d0`
  và chunk p31–57 hiện đều `SUCCEEDED`, cùng bind manifest
  `gfdmv1:manifest:47f071614e0114e87925984f37c6f35f3291011b35a889bf761046410d7c6dfe`
  và selection
  `gjfcdmsv1:selection:0e6d44b696452ab5628b9ddb8ea1390f84562281e5d56865f25888eabb49153e`.
  Receipt deferral/lỗi 429 vẫn được giữ làm lịch sử nhưng không còn là blocker.

- **GJF-CLOSED-019:** khi chuyển corpus sang OpenRouter-only, một document
  retry trước đây gửi lại toàn bộ trang dù đa số trang Google đã có JSON hợp
  lệ. Điều này vừa tốn token, vừa tạo nhiều version cùng prompt/schema/image.
  Bộ tăng tốc hiện kiểm tra riêng từng trang bằng source/image/prompt/schema và
  route receipt: chỉ frontier thật sự chưa có version mới được gửi; duplicate
  cùng một route vẫn fail-closed. Probe HDB H1/2025 công ty mẹ tìm đúng 33
  trang thiếu `[20,28,31..61]`, giữ nguyên 28 trang đã có và gọi OpenRouter với
  `--workers 5`; không gửi lại toàn bộ 61 trang. Cả 33 trang thành công và ba
  chunk được đóng bằng manifest
  `gfdmv1:manifest:5d3a2e901535f38754405f010286ed9f78fee28fd058f07dd82e52cec47da986`,
  selection
  `gjfcdmsv1:selection:f98fde5070b85471ea2fef603ea9cd0f38af3de462218914f4a879bff0ae1b34`.
  Cùng primitive đó chỉ gửi `[11,30]` cho CTG Q2/2026 công ty mẹ và
  `[11,24,34,53]` cho CTG Q2/2026 hợp nhất; hai document 61 trang đều đóng đủ,
  thay vì gửi lại 61 ảnh mỗi document.

- **GJF-CLOSED-018:** CTG H1/2026 hợp nhất từng có hai version hợp lệ trên
  cùng trang (Google Batch và OpenRouter), khiến manifest cũ từ chối với
  `page frontier is incomplete or duplicate`. Store vẫn giữ cả hai version,
  nhưng manifest mới niêm phong một thứ tự provider rõ ràng và tái lập được:
  `OPENROUTER/flex` → `GOOGLE_GEMINI_BATCH_API/batch` →
  `GOOGLE_GEMINI_API/standard`. Thứ tự này là một permutation đầy đủ của route
  được phép và được hash trong extraction contract; thiếu route, lặp route hay
  còn hai version trong cùng route đều bị từ chối. CTG 60 trang replay chọn
  đúng 60/60 version OpenRouter, manifest
  `gfdmv1:manifest:057b0e8ffdd4bf44081a2f7bf5d7d4b138a6e23c13bcaf92a31ea30ee60a42c8`
  và đóng ledger mà không gọi provider thêm (`provider_results=[]`).

- **GJF-CLOSED-017:** kiểm toán độc lập ảnh nguyên trang sau phản hồi về góc
  ảnh bị mất đã duyệt lại toàn bộ 8.947 trang nguồn bằng primitive hiện hành,
  không dùng geometry để suy luận nội dung. Có 644 trang mà canvas được mở
  rộng khỏi page box khai báo. Trong 636 trang đã có kết quả OCR tại thời điểm
  kiểm tra, ảnh được render lại trực tiếp từ PDF ở 300 DPI đều khớp tuyệt đối
  `image_sha256`, chiều rộng và chiều cao với page-version đang nằm trong
  database (`636/636`, mismatch `0`). Tám trang còn lại chưa OCR nên không có
  stale version để giữ và sẽ dùng renderer mới ngay từ request đầu. Vì cache key
  bind image SHA, mọi ảnh crop cũ khác byte tự động trở thành version lịch sử,
  không được manifest hiện hành chọn.

- **GJF-CLOSED-016:** MBB quý 4/2025 hợp nhất p57/p60 là hai bảng ngang có
  tương ứng 8 và 7 cột. Các lượt `simple`/`items`/`balanced` cũ liên tục ghép
  glyph dấu gạch vào số, sinh ký tự lạ và trả vector ngắn hơn `columns`; validator
  giữ đúng trạng thái fail-closed. Primitive retry cuối tại commit
  `ff064a463031dc2b7f0c2a1475733f31da500f30` buộc mỗi ô chỉ có dấu gạch thành
  chuỗi `"0"`, cấm nối dấu gạch vào số lân cận, đồng thời chuyển semantic failure
  phát sinh sau một provider retry tiếp tục qua `items` rồi `balanced`. Trên đúng
  hai ảnh nguyên trang 300-DPI SHA `c1a5dbea...`/`bb4f8a26...`, kết quả mới có
  22 hàng × 8 cột và 22 hàng × 7 cột, không ký tự lạ, không vector lệch; mọi hàng
  số đều thỏa tổng ngang nhìn thấy. Hai request dùng 3.093+3.093 input và
  2.459+2.311 output token, tổng chi phí `0.00563175 USD`. Manifest 61 trang
  `gfdmv1:manifest:af4d48e352dd92cb43683a512f9346c6cb374203fbb5ab2efad93138e63443e4`,
  selection
  `gjfcdmsv1:selection:deb0df27830a24e43fac1333b0729ae7606365d5f8dd56c176d661ecc0d6c91e`
  chứa 736 hàng/2.417 ô, không unresolved; ba Google chunk đều được niêm phong
  `SUCCEEDED` mà không gọi lại 59 trang đã hợp lệ.

- **GJF-CLOSED-015:** HDB quý 2/2025 công ty mẹ được phục hồi tăng dần mà
  không gọi lại trang đã hợp lệ. Lần đầu đóng 50/57 trang; `items` đóng p12,
  p31, p36, p50 và `simple` đóng p23, còn p13/p43 gặp provider error. Lần resume
  cuối lấy cache cho mọi page-version đã có, `simple` đóng p13 và `items` đóng
  p43. Hai trang cuối đều dùng ảnh nguyên trang 300-DPI, trả
  `all_relevant_content_transcribed=true`, không uncertainty: p13 dùng 2.592
  input/959 output token, `0.0013850625 USD`; p43 giữ hai bảng 17 hàng/62 ô,
  dùng 2.620 input/1.362 output token, `0.001768125 USD`. Manifest 57 trang
  `gfdmv1:manifest:47f071614e0114e87925984f37c6f35f3291011b35a889bf761046410d7c6dfe`,
  selection
  `gjfcdmsv1:selection:0e6d44b696452ab5628b9ddb8ea1390f84562281e5d56865f25888eabb49153e`
  chứa 601 hàng/1.883 ô và không unresolved; cả hai Google task p1–30/p31–57
  được niêm phong `SUCCEEDED` cùng một document receipt.

- **GJF-CLOSED-014:** ACB kiểm toán năm 2025 công ty mẹ trang vật lý 57 có
  rotation 270° và khai `MediaBox/CropBox` 595,68×842,40 pt, trong khi ảnh scan
  thật được đặt từ x=-124,277 tới x=719,957 pt. Renderer mặc định vì vậy tạo ảnh
  3.510×2.482 px, SHA
  `97aa43fa86cac8c39f45d82ecd0f951926c4dccfbb0e5a375bd757470a7c6301`
  và cắt cả hai mép. Cả prompt `simple` Batch lẫn retry `items` đều fail-closed
  `UNRESOLVED_PAGE`, báo chính xác cột `Lợi nhuận chưa phân phối` và các cột sau
  bị mất. Whole-page renderer không crop theo bảng: nó mở canvas nguồn có giới
  hạn tới toàn bộ painted-content bounds, tạo ảnh 300-DPI 3.510×3.535 px, SHA
  `ea85078c1f6b78f1e62dfcb7563d12f431cb2e58f62b0f452b5ea4382289f91b`.
  Retry `items` trên đúng ảnh mới trả đủ 7 cột, 13 hàng/91 ô, gồm cột `Tổng cộng`,
  `all_relevant_content_transcribed=true` và không uncertainty; 1.329 input,
  2.301 output, 1.279 thought token, chi phí `0.01442175 USD`. Manifest hiện hành
  `gfdmv1:manifest:8c790eda5208e8c3ba815630740928174ae66611b347822f121cf1bf95059da6`
  bind image SHA mới; hai JSON version ảnh cũ chỉ còn là lịch sử và không được
  chọn.

- **GJF-CLOSED-013:** VCB quý 2/2026 hợp nhất có bốn provider-fail ở p8/9/14/15;
  retry `simple` đóng p8/14/15, còn p9 chuyển thành typed semantic lệch hàng/cột.
  Một retry `items` trên ảnh nguyên trang SHA
  `f8fad430bd33312a21108bf29b4ae00284c0fcd7c984d3d2b1e0fa3dcb3bd793`
  trả đúng bảng 11 hàng × 4 cột, page JSON SHA
  `7e6d2a62f0c1eddb4dc8961e92d9c105541e5fa3bee4d8c1123689ed4fc7b306`,
  2.608 input/1.009 output token, `0.0014349375 USD`. Manifest 55 trang
  `gfdmv1:manifest:8e986903b8bc1e15449025d90e29a6dddebf260870174c8e9e4877b236dfcc1e`,
  selection
  `gjfcdmsv1:selection:18144959efba781d8e31860ba08f7bb147805b1283d75c9e488c61658320985b`
  chứa 506 hàng/1.973 ô, không unresolved.

- **GJF-CLOSED-011:** HDB quý 3/2025 hợp nhất đóng đủ 55 trang sau bốn
  page-local recovery: p9 `items` sửa lệch hàng/cột (27×3); p22 retry `simple`
  sau provider-error; p26 `balanced` sửa hierarchy/title không hợp lệ (32×2);
  p36 retry `items` sau provider-error (21 hàng, hai bảng). Bốn ảnh nguyên trang
  có SHA lần lượt `0ba9d42a...`, `5ccfd83d...`, `7c84127b...`, `be008162...`;
  page JSON SHA `cffca6ed...`, `d7947179...`, `eff02c05...`, `55724d91...`.
  Manifest
  `gfdmv1:manifest:79b339a8672b5d1fdac5e0d8b101f11413b790687891ba54dc0862df42f03209`,
  selection
  `gjfcdmsv1:selection:7d1f666dd0b7e24ee4d25936fa26ab8c0d7cf3b04311cb8584e7b542d7da1ad5`
  chứa 617 hàng/1.909 ô, không unresolved. Chi phí bốn request thành công là
  `0.009117 USD`; các attempt provider-error/429 được giữ riêng trong usage
  ledger thay vì gộp vào selected-manifest cost.

- **GJF-CLOSED-010:** VCB quý 3/2025 hợp nhất trang vật lý 42 là bảng báo cáo
  bộ phận có sáu cột tiền. Prompt `simple` vừa khai thêm một cột nhãn `TEXT`,
  vừa bỏ placeholder tại các ô trống nên nhiều hàng không thể bind chắc chắn
  với cột. Retry `items` trên ảnh nguyên trang SHA
  `560bda8d58fd43b06943726fc901023eaac422d8ea85e55a4f7166d29ccb5d92`
  trả một bảng 21 hàng × 6 cột, page JSON SHA
  `ef16f6c1c657368b80a3dbb9479be6eb5d7637d73df743fbf0a7854b9cc6b4ed`,
  dùng 2.608 input/2.051 output token và `0.0024118125 USD`. Tài liệu 54 trang
  đóng manifest
  `gfdmv1:manifest:cd9b58d9c593159928a0883511119612666da6d18eec2338cf54ed93fd266195`,
  selection
  `gjfcdmsv1:selection:3154b2419904877b8b2086aab42413a4ccfe2f20914d3f9f3c3888f8faad01fc`,
  495 hàng/1.938 ô, không unresolved.

- **GJF-CLOSED-009:** HDB quý 1/2025 hợp nhất trang vật lý 29 có một cột nhãn
  và hai cột tiền. Prompt `simple` đưa nhầm cột nhãn vô danh vào `columns` nên
  JSON khai ba cột nhưng mọi hàng chỉ có hai giá trị; validator từ chối thay vì
  tự đoán. Retry `items` trên ảnh nguyên trang SHA
  `7ca751394093d874050c7de70838afbd812a19d5141ca9c434f59029bf2a2d0f`
  trả đúng một bảng 32 hàng × 2 cột, page JSON SHA
  `050e0f125acb651f0766545e92c3ebac95e4e9490ca7d158bfeb26675c37df9a`,
  dùng 2.620 input/2.249 output token và `0.0025996875 USD`. Tài liệu 54 trang
  đóng manifest
  `gfdmv1:manifest:882493af284b8f8f077b37dd6ce5af6fe75b8ffd722c8d49da6a4486bd13c806`,
  selection
  `gjfcdmsv1:selection:6a5f00d832560d7c855157f021be4a9b962a51073fcd8781ea69c4e4d61578c4`;
  trang 40 bị provider lỗi được retry `simple` độc lập, không thay đổi prompt
  của 53 trang còn lại.

- **GJF-CLOSED-008:** VCB quý 1/2026 hợp nhất trang vật lý 34 là bảng biến
  động vốn 11 cột. Prompt `simple` và `items` đều chép đúng tiêu đề/số nhìn
  thấy nhưng bỏ placeholder ở các ô trống, làm một số hàng chỉ còn 10 hoặc 9
  phần tử và bị validator từ chối. Một retry `balanced` trên đúng ảnh nguyên
  trang 300-DPI SHA
  `8f8478d321b6fe95fcad8d24156291d68777c2083f5f57296cb161aafd558447`
  trả 7/7 hàng, mỗi hàng đúng 11 vị trí; page JSON SHA
  `d557be04acf3bd61f765c867b14c41d4a853191d0dcb2bae58c2f08467c2c849`.
  Request dùng 3.059 input/1.077 output token, chi phí `0.00158325 USD`.
  Manifest 53 trang
  `gfdmv1:manifest:d0d157d684fb8ec1a2cbabde32572c108e4af98b2187b79abc0da9bbeeee93bd`,
  selection
  `gjfcdmsv1:selection:09fd6a6ab54d90a1639f72165c6aeabed27c99ef1f80a9f31eba8dcef77f58fc`
  đã đóng với 485 hàng/1.866 ô và không gửi lại 52 trang hợp lệ.

- **GJF-CLOSED-007:** VCB quý 3/2025 công ty mẹ trang vật lý 40 có bảng 5 cột;
  prompt `simple` và `items` chép đúng số nhìn thấy nhưng bỏ vị trí của ô trống,
  nên fail-closed vì vector hàng lệch cột. Retry duy nhất bằng prompt `balanced`
  trên cùng ảnh nguyên trang SHA `01c6e5fdf99bc4211bf93fa693bb7811f6dfaf464a6c82fd9830c62aaa0cca42`
  đã giữ `null` cho ô trống và đóng manifest 52 trang
  `gfdmv1:manifest:f79ea864e247b3fa2cd0c841e9a5c9439de9aa57401ad1b823b9cc572d7fdebf`,
  selection `gjfcdmsv1:selection:5aeb88f2221bb8af5dffc2cf32bf8036d97021498f583c7b9b58e0ebd42b95d0`;
  505 hàng/1.807 ô, không unresolved. Cơ chế resume xác thực lại đủ 52 image SHA
  rồi niêm phong cả hai chunk mà không gửi lại 51 trang đã hợp lệ.

- **GJF-CLOSED-006 (trước đây GJF-OPEN-001):** ACB H1/2025 hợp nhất trang vật
  lý 22 đã được render lại nguyên trang 300 DPI, 2.482×3.510 px, SHA-256
  `817a51eef6fae2102c81f99e813604dd19522463d49e2c8c8b00353a66e9f4fa`.
  SHA ảnh cũ `e2487e9276543295cb1d89e34633b8ea100d2e2e4174259ba9a5793332f5c296`
  là version stale và không còn authority. Prompt `scope` xác nhận đúng đây là
  bảng tỷ lệ/chính sách, trả `NO_RELEVANT_FINANCIAL_CONTENT`, `sections=[]`, 0
  hàng/ô; input 2.630, output 36, tổng 2.666 token, chi phí `0.000526875 USD`.
  Manifest hiện hành là
  `gfdmv1:manifest:468d56a4089c88e72192fe618c0288b6b0c30263d5b534e8beeeb42811fe4111`,
  được chọn bằng receipt append-only
  `gjfcdmsv1:selection:6929ee022fcfd311288838caf20f25913a8962fb4186eac6430e8a7038b71019`;
  kết quả `simple` cũ vẫn được giữ làm lịch sử nhưng không được chọn.

- **GJF-CLOSED-001:** validator V16 replay được 21/21 trang CTG semantic-failed
  từ raw response bất biến, không gọi API lại; một task 61 trang đóng hoàn toàn
  với 15 trang replay và 46 cache hit.
- **GJF-CLOSED-002:** prompt `items` xử lý đúng sáu ca `RECITATION`/prose mẫu:
  bốn trang trả tối thiểu `NO_RELEVANT`, hai trang giữ đúng bảng/khoản mục. Tổng
  chi phí positive `0.012789 USD`; mỗi version giữ prompt hash riêng.
- **GJF-CLOSED-003:** validator V21 replay generic các ô blank `""`, hierarchy
  cell gộp dọc từ đúng hàng liền trước và một zero/dash bị bỏ khi phương trình
  hai hàng chi tiết bằng tổng khép mọi cột. MBB 2026 quý 1 công ty mẹ (57 trang)
  đóng manifest `gfdmv1:manifest:5403ee04dcc15db0c32ab703266dc99908353ec4ae92f1887fe0bf79af7a5cf5`
  mà không gọi API lại; test JSON-first `108 passed`.
- **GJF-CLOSED-004:** mười trang full-page Google `RECITATION` thuộc tám tài
  liệu BID/CTG/HDB/MBB đã được đọc lại bằng prompt `items`: hai trang giữ đúng
  bảng/khoản mục và tám trang trả tối thiểu `NO_RELEVANT`. Manifest V3 khóa
  prompt SHA riêng theo từng trang; các document manifest lần lượt là
  `112ef17d...`, `27bab718...`, `380eb513...`, `f7ebf7f4...`, `2b47dc1c...`,
  `70cd19f4...`, `95f54df3...`, `7571b091...`. Request là độc lập,
  `store=false`, không history/cachedContent; `RECITATION` được xác nhận là
  output filter qua response ID/citation metadata, không phải context cũ.
- **GJF-CLOSED-005:** validator V23 loại đúng một cột đầu vô danh
  `UNKNOWN` khi mọi hàng đã bind nhãn qua hierarchy và mọi cell còn lại khớp
  chính xác kiểu cột. VCB Q1/2025 công ty mẹ trang 9 replay thành báo cáo lưu
  chuyển tiền tệ 27 hàng x 2 kỳ; tài liệu đóng manifest
  `gfdmv1:manifest:14d952f9b46f3b649e9d1109c6d0b907bc2c27461c1a66b85c942b4b13155a02`.
  VCB Q4/2025 hợp nhất dùng prompt `items` cho trang 15, 16, 48 và đóng manifest
  `gfdmv1:manifest:d7255dda636150bb2a47768b144f59798e811c048cc30d3a25eee333347b0c89`;
  trang 48 giữ đủ 10 hàng x 11 cột. VIB H1/2025 công ty mẹ trang 19 cũng được
  phân loại `NO_RELEVANT` bằng prompt `items` và đóng manifest
  `gfdmv1:manifest:84c23ab374f5b7846d56992083147b4613e4bbe58b66c722b8e9a7cd3db6d2bf`.

## SUPERSEDED / historical references

Chưa có. Khi dẫn case từ `UNRESOLVED_MAPPING_LEDGER.md`, phải giữ nguyên ID,
artifact hash và trạng thái lịch sử, đồng thời ghi rõ version pipeline mới.
