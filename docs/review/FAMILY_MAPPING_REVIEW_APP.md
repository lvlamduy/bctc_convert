# Ứng dụng kiểm tra Gemini và mapping schema

Ứng dụng Flask này dùng để kiểm tra trực quan kết quả family theo từng PDF. Màn
hình đối chiếu đặt cạnh nhau:

1. ảnh đúng trang PDF nguồn;
2. bảng canonical do Gemini đọc;
3. mapping vào schema gồm `ReportNormId`, tên khoản mục, vai trò, kỳ và giá trị.

Ứng dụng chỉ đọc dữ liệu; không sửa results store, page store, PDF hay schema.

## Khởi chạy

Từ thư mục gốc repository:

```bash
uv sync --extra dev
uv run python scripts/review/run_family_review_app.py
```

Mở <http://127.0.0.1:8000>. Cổng mặc định là **8000**.

Ứng dụng tự nhận các artifact production hiện có trên máy phát triển. Khi chạy
ở máy khác, cấu hình các đường dẫn sau:

```bash
export BCTC_FAMILY_RESULTS_DB=/duong-dan/family-results.sqlite3
export BCTC_PAGE_STORE_DB=/duong-dan/page-store.sqlite3
export BCTC_PDF_ROOT=/duong-dan/vietstock_bctc
export BCTC_SCHEMA_PATH=/workspace/bctc-ai/reference/schemas/schema_graph.jsonl
uv run python scripts/review/run_family_review_app.py
```

Các biến tùy chọn:

- `BCTC_REVIEW_HOST`: địa chỉ bind, mặc định `0.0.0.0`;
- `BCTC_REVIEW_PORT`: cổng, mặc định `8000`;
- `BCTC_REVIEW_CACHE_DIR`: nơi cache ảnh trang đã render;
- `BCTC_REVIEW_DEBUG=1`: bật Flask debug khi phát triển.

## Ghép nhiều corpus/run mà không sửa selection production

Để xem chung tám ngân hàng cũ và mười chín ngân hàng mới, đặt
`BCTC_REVIEW_RUN_MANIFEST` tới một JSON review-only. Mỗi nguồn khóa chính xác
family, run, results DB, page DB và thư mục PDF:

```json
{
  "format_version": "BCTC_FAMILY_REVIEW_RUN_MANIFEST_V1",
  "sources": [
    {
      "family_id": "LOAN_QUALITY_CLASSIFICATION",
      "family_run_id": "run-cu-da-xac-thuc",
      "results_database": "/data/old-8/family-results.sqlite3",
      "page_database": "/data/old-8/page-store.sqlite3",
      "pdf_root": "/workspace/bctc-ai/vietstock_bctc"
    },
    {
      "family_id": "LOAN_QUALITY_CLASSIFICATION",
      "family_run_id": "run-moi-da-xac-thuc",
      "results_database": "/data/new-19/family-results.sqlite3",
      "page_database": "/data/new-19/page-store.sqlite3",
      "pdf_root": "/workspace/bctc-ai/vietstock_bctc"
    }
  ]
}
```

Sau đó chạy:

```bash
export BCTC_REVIEW_RUN_MANIFEST=/data/review/27-bank-family-runs.json
uv run python scripts/review/run_family_review_app.py
```

Manifest có thể chứa nhiều run nguồn cho cùng family. Dashboard cộng các số
liệu và hợp nhất danh sách PDF theo `source_sha256`, nhưng vẫn đọc từng DB ở chế
độ chỉ đọc. Run không cần trở thành `family_current_selection`; vì vậy review
27 ngân hàng không thay đổi selection lịch sử. Cấu hình bị trùng PDF trong cùng
family hoặc trỏ sai `family_run_id` sẽ bị từ chối trước khi server nhận traffic.

Không cần viết manifest bằng tay. Sau khi all-family receipt của 19 ngân hàng
mới hoàn tất, tạo manifest từ selection cũ, receipt mới và Family 30 bổ sung:

```bash
uv run python scripts/review/build_family_review_run_manifest.py \
  --current-source OLD_RESULTS.sqlite3 OLD_PAGES.sqlite3 /workspace/bctc-ai/vietstock_bctc \
  --explicit-source NET_INTEREST_INCOME OLD_FAMILY30_RUN OLD_FAMILY30.sqlite3 \
    OLD_PAGES.sqlite3 /workspace/bctc-ai/vietstock_bctc \
  --receipt-source NEW_19_RUN_RECEIPT.json NEW_19_RESULTS.sqlite3 \
    NEW_19_PAGES.sqlite3 /workspace/bctc-ai/vietstock_bctc \
  --output /data/review/27-bank-family-runs.json
```

Builder mở các SQLite ở chế độ chỉ đọc, xác minh run thuộc đúng family, số PDF
khớp trial frontier, mọi source SHA có trong page store và đúng file PDF còn tồn
tại. Nó cũng chặn hai run của cùng family chứa trùng PDF. Output là write-once:
nếu file đã tồn tại với nội dung khác, lệnh dừng thay vì ghi đè.

Nếu page store và results store có sẵn nhưng thiếu `BCTC_PDF_ROOT`, người dùng
vẫn xem được dữ liệu Gemini và mapping. Cột ảnh sẽ báo rõ chưa có file PDF thay
vì âm thầm hiển thị sai trang.

## Luồng kiểm tra

1. Chọn family ở cột trái. Family được đánh số và sắp theo đúng thứ tự nghiệp
   vụ/schema của dashboard (ví dụ **8. Phân tích chất lượng cho vay**).
2. Lọc ngân hàng, năm, quý/6 tháng/năm, loại hợp nhất/riêng lẻ/công ty mẹ và
   tình trạng kiểm toán.
3. Chọn file PDF.
4. Chọn trang liên quan nếu family trải trên nhiều trang.
5. Nhấn một mapping ở cột phải để chuyển tới đúng trang/bảng và làm nổi dòng
   Gemini nguồn tương ứng.

Trong cột PDF, giữ chuột và kéo để di chuyển theo cả bốn hướng. Hai vạch đứng
giữa các cột là tay nắm thay đổi độ rộng; kéo trái/phải để ưu tiên phần đang
kiểm tra, nhấp đúp để trả về bố cục mặc định.

## Chú giải mapping

- **Đã map trực tiếp**: dòng PDF đi thẳng vào ReportNormId.
- **Đã map qua quy tắc**: dòng nguồn tham gia một phép tính/đối chiếu xác định
  duy nhất rồi đi vào ReportNormId. Đây là mapping hợp lệ.
- **SOURCE_ONLY / CONTROL**: dòng được giữ để kiểm tra tổng hoặc cấu trúc nhưng
  không phải khoản mục đích của family; không mặc nhiên là thiếu schema.
- Trạng thái `DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER` được giao diện diễn giải
  là “Giá trị được tính chính xác từ các dòng nguồn đã xác thực”. Mã kỹ thuật
  chỉ hiện khi người dùng mở **Chi tiết kỹ thuật**.

`NOT_OBSERVED` được hiển thị như một kết quả bình thường: không có bảng ứng viên
vì family không xuất hiện trong phạm vi PDF. `UNRESOLVED` hiển thị nguyên nhân
dễ đọc trong dải cảnh báo và phần chẩn đoán cuối màn hình.
