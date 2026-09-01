# Gemini JSON-first family progress

Đây là bảng tiến độ làm lại từ đầu sau khi toàn corpus đã có immutable page
JSON. Thứ tự bắt buộc là Family 1 đến Family cuối cùng; không bắt đầu ở Family
12. `COMPLETED_TM_FAMILIES.md` vẫn là hồ sơ lịch sử và không bị thay thế.

## Corpus ingestion checkpoint

- Checkpoint vận hành 2026-08-27: ledger đã đóng `8.429/8.947` trang
  (`94,21%`) và `135/140` tài liệu; còn `518` trang trong `5` tài liệu. Đây
  vẫn chưa phải corpus freeze và chưa cấp quyền chạy Family 1.
- Mọi request mới từ checkpoint này chạy duy nhất qua OpenRouter với model
  `google/gemini-3.7-flash`, provider Google Vertex Flex và tối đa 25 request
  hữu ích song song. Google standard, Google Batch và Google fallback đều bị
  vô hiệu hóa; các page-version Google cũ chỉ được giữ làm lịch sử/cache.
- Usage tại checkpoint: 19.648.259 input tokens, 12.700.766 output tokens,
  455.229 thought tokens; chi phí cộng dồn `22.952865937500 USD`, trong đó
  `11.038881937500 USD` là OpenRouter và `11.913984000000 USD` là các lượt
  Google đã hoàn thành trước khi bị vô hiệu hóa.
- Supervisor lưu ngay từng raw/canonical page JSON, retry theo đúng page và
  không gửi lại các page đã cache. Sau khi đủ 8.947 trang, lệnh freeze sẽ replay
  ảnh nguyên trang/prompt/provider selection, snapshot store+ledger và mới công
  bố số phân loại page chính thức.

| Family | Trạng thái JSON-first | Bằng chứng |
|---:|---|---|
| 1 | PENDING_COMPLETE_CORPUS_JSON_FREEZE | Chưa chạy mapping |

Các family tiếp theo chỉ được thêm khi Family trước có disposition chính thức
hoặc blocker được ghi rõ trong unresolved ledger mới.
