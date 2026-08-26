# Gemini JSON-first unresolved ledger

Ledger này chỉ dành cho pipeline Gemini JSON-first. Case đang `OPEN` phải luôn
được đặt trước các phần `CLOSED` và `SUPERSEDED`. Không dùng file này để sửa
lại trạng thái lịch sử của pipeline PP-OCR/VietOCR/geometry.

## OPEN — current

### GJF-OPEN-001 — ACB H1/2025 hợp nhất, trang vật lý 22

- **Source:** `vietstock_bctc/ACB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm
  2025.pdf`, trang 22, ảnh 300 DPI SHA-256
  `e2487e9276543295cb1d89e34633b8ea100d2e2e4174259ba9a5793332f5c296`.
- **Nội dung:** một bảng 5 nhóm nợ/tỷ lệ dự phòng và một bảng tài sản bảo đảm
  nhiều hàng/tỷ lệ khấu trừ.
- **Failure:** Google standard với prompt `simple`, `items` và `balanced` đều
  trả `RECITATION` cho nguyên trang; crop chỉ bảng 5 nhóm nợ cũng bị chặn.
  OpenRouter sync hết hai zero-usage retry.
  OpenRouter Batch base64 bị từ chối; S3-presigned URL vượt input gate nhưng
  Vertex Batch trả typed failure rằng Gemini adapter không hỗ trợ ảnh.
- **Partial evidence:** crop bảng tài sản bảo đảm thành công qua Google standard,
  tách đúng 12 hàng/12 ô, 11 ô có giá trị; các cặp 50/30% và 30/10% không còn bị
  gộp. Chi phí request thành công `0.0092775 USD`. Kết quả này chưa đủ để đóng
  toàn trang vì bảng 5 nhóm nợ còn thiếu.
- **Disposition:** `OPEN`. Không thay bằng `NO_RELEVANT`, không dùng OCR cũ,
  không suy/chép tay 5 tỷ lệ vào authority. Hướng tiếp theo phải là fallback LLM
  ảnh độc lập hoặc một tiled-page receipt có coverage/dedup exact và không né
  provider safety.

## CLOSED — current

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
