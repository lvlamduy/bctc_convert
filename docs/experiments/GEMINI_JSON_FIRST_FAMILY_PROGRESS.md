# Gemini JSON-first family progress

Đây là bảng tiến độ làm lại từ đầu sau khi toàn corpus đã có immutable page
JSON. Thứ tự bắt buộc là Family 1 đến Family cuối cùng; không bắt đầu ở Family
12. `COMPLETED_TM_FAMILIES.md` vẫn là hồ sơ lịch sử và không bị thay thế.

## Corpus ingestion checkpoint

- Checkpoint 2026-08-26: `2.197/8.947` trang có page JSON hợp lệ (24,6%),
  thuộc 39 tài liệu; 37/140 tài liệu đã hoàn tất toàn bộ task tại checkpoint.
- Phân loại theo version mới nhất của từng trang: 1.777 trang thuyết minh, 243
  trang báo cáo tài chính chính, 176 trang không có nội dung tài chính liên quan
  và 1 trang `UNRESOLVED_PAGE`.
- Usage cộng dồn: 4.416.181 input tokens, 3.332.802 output tokens, 118.295
  thought tokens; chi phí ước tính/billed cộng dồn `7.6885764375 USD`.
- Supervisor V23 đang chạy tiếp Google Batch và OpenRouter; checkpoint này chưa
  phải corpus freeze. ACB H1/2025 hợp nhất trang 22 là trang provider-filter
  duy nhất đang OPEN, không chặn các task còn lại.

| Family | Trạng thái JSON-first | Bằng chứng |
|---:|---|---|
| 1 | BLOCKED_BY_CORPUS_JSON_INGESTION | Chưa chạy mapping |

Các family tiếp theo chỉ được thêm khi Family trước có disposition chính thức
hoặc blocker được ghi rõ trong unresolved ledger mới.
