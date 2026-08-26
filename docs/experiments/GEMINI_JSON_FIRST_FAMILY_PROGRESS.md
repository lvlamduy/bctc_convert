# Gemini JSON-first family progress

Đây là bảng tiến độ làm lại từ đầu sau khi toàn corpus đã có immutable page
JSON. Thứ tự bắt buộc là Family 1 đến Family cuối cùng; không bắt đầu ở Family
12. `COMPLETED_TM_FAMILIES.md` vẫn là hồ sơ lịch sử và không bị thay thế.

## Corpus ingestion checkpoint

- 2026-08-26: `1.756/8.947` trang có page JSON hợp lệ, thuộc 33 tài liệu.
- Phân loại: 1.414 trang thuyết minh, 204 trang báo cáo tài chính chính, 137
  trang không có nội dung tài chính liên quan và 1 trang `UNRESOLVED_PAGE`.
- Usage cộng dồn: 3.534.138 input tokens, 2.698.525 output tokens, 86.731
  thought tokens; chi phí ước tính/billed cộng dồn `6.3260000625 USD`.
- Supervisor V21 đang resume ledger cũ; checkpoint này chưa phải corpus freeze.

| Family | Trạng thái JSON-first | Bằng chứng |
|---:|---|---|
| 1 | BLOCKED_BY_CORPUS_JSON_INGESTION | Chưa chạy mapping |

Các family tiếp theo chỉ được thêm khi Family trước có disposition chính thức
hoặc blocker được ghi rõ trong unresolved ledger mới.
