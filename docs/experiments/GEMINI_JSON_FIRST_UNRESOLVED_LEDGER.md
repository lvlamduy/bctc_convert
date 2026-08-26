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
- **Failure:** Google standard với prompt `items` trả `RECITATION` cho nguyên
  trang và crop chỉ bảng 5 nhóm nợ. OpenRouter sync hết hai zero-usage retry.
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

## SUPERSEDED / historical references

Chưa có. Khi dẫn case từ `UNRESOLVED_MAPPING_LEDGER.md`, phải giữ nguyên ID,
artifact hash và trạng thái lịch sử, đồng thời ghi rõ version pipeline mới.
