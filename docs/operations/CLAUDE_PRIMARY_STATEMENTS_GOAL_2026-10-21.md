# Mục tiêu số hóa ba bảng báo cáo tài chính cho Claude

Ngày giao việc: 21/10/2026. Người thực hiện: Claude. Người phối hợp và tích hợp: Codex.

Claude xây dựng và hoàn thiện thuật toán số hóa **ba bảng chính** của báo cáo tài chính ngân hàng: cân đối kế toán, kết quả kinh doanh và lưu chuyển tiền tệ. Codex tiếp tục phụ trách **thuyết minh báo cáo tài chính** và các family đang dang dở. Hai bên phát triển song song trong các worktree và nhánh riêng, không sửa chồng mã hoặc dữ liệu nguồn.

Đọc kèm [hướng dẫn triển khai](CLAUDE_PRIMARY_STATEMENTS_INSTRUCTIONS_2026-10-21.md) trước khi sửa code.

## Đầu vào và đầu ra

Đầu vào cuối cùng là PDF báo cáo tài chính scan, native hoặc mixed. Trong đợt phát triển này, sử dụng lại Gemini JSON đã lưu và được chọn trong database; không OCR lại và không gọi provider.

Luồng bắt buộc:

```text
PDF nguồn
  -> Gemini JSON gốc đã lưu trong database
  -> xác thực nguồn và cấu trúc
  -> nhận dạng bảng, hàng, cột, kỳ, đơn vị và phạm vi báo cáo
  -> hiểu quan hệ kế toán và ánh xạ schema
  -> kiểm tra, lưu kết quả và bằng chứng trong SQLite
  -> đọc lại và kiểm chứng độc lập
  -> Excel theo schema và template hiện hành
```

Sản phẩm phải có dữ liệu có cấu trúc, database kết quả, file Excel ba bảng và bằng chứng truy ngược từng ô về nguồn. Không coi JSON hợp lệ, nhiều test xanh hoặc một workbook đúng bố cục là đã số hóa đúng.

## Phạm vi Claude sở hữu

| Bảng | Loại cấu trúc nguồn | Phạm vi cần xử lý |
| --- | --- | --- |
| CDKT | BALANCE_SHEET | Tài sản, nợ phải trả, vốn chủ sở hữu; số dư tại đúng ngày |
| KQKD | INCOME_STATEMENT | Thu nhập, chi phí, lợi nhuận, thuế; đúng quý, lũy kế hoặc năm được in |
| LCTT | CASH_FLOW | Phương pháp trực tiếp và gián tiếp; hoạt động kinh doanh, đầu tư, tài chính và biến động tiền |

Phạm vi là các ngân hàng trong corpus được phục hồi và báo cáo từ năm 2025 đến hiện tại. PDF năm 2024 không thuộc production hoặc hàng đợi provider. Số so sánh năm 2024 **được in trong một báo cáo từ 2025 trở đi** vẫn là dữ liệu so sánh hợp lệ khi đã xác thực kỳ.

Thuật toán phải dùng chung được cho nhiều ngân hàng, nhiều layout, báo cáo riêng hoặc hợp nhất, kiểm toán hoặc soát xét, quý hoặc năm và bảng nối qua nhiều trang. Không viết nhánh theo mã ngân hàng, tên file, số trang hoặc giá trị cụ thể để làm khớp một báo cáo.

## Ranh giới với phần thuyết minh

Claude không sửa family TM, F39, F36, F37 hoặc mở family TM mới. Không sửa schema, template, manifest, database nguồn hay hai shared files đang frozen nếu chưa có review riêng của Codex.

KQKD vẫn bao gồm các dòng thuế được in trong chính bảng KQKD. Điều này không cấp quyền sửa family thuyết minh thuế F39. Cùng một khái niệm kinh tế xuất hiện ở hai nơi không cho phép dùng nhầm ReportNormId hoặc ghi đè kết quả của nhau.

Codex được đọc PRIMARY nguồn để đối chiếu thuyết minh. Kết quả đề xuất của Claude không thay thế PDF hoặc Gemini JSON gốc làm nguồn xác thực cho Codex.

## Schema và nguyên tắc số liệu

Snapshot tại thời điểm bàn giao là `UNIVERSAL_BANK_BCTC_SCHEMA@6076`: CDKT 99 mục, KQKD 25 mục, LCTT 110 mục, TM 1.721 mục; tổng 1.955 mục. Ba bảng chính có 234 mục schema, **không có nghĩa mọi báo cáo phải chứa 234 giá trị số**. Registry và template được xác minh bằng hash là authority; BASE_SCHEMA 1.593 mục chỉ là nền lịch sử.

Giữ nguyên ReportNormId, ý nghĩa kế toán, quan hệ cha con và DisplayOrder. Không dùng độ lớn của ReportNormId làm thứ tự trình bày. Khái niệm mới có bằng chứng phải được báo thành schema gap để review, không ép vào chỉ tiêu gần tên nhất hoặc bỏ vĩnh viễn dưới nhãn source-only.

Giữ nguyên số đọc được, dấu âm dương, raw text, đơn vị và trạng thái từng ô. Blank không thành 0; thiếu ô không được suy từ tổng. Không suy đơn vị từ độ lớn, không đổi dấu để làm phương trình đúng, không suy quý hoặc lũy kế từ tên PDF. Phân biệt dấu gạch chưa có nghĩa số với `DASH_ZERO` được chính sách số liệu cho phép và đã xác thực.

## Điều kiện hoàn thành

1. Có thuật toán chạy từ database cho cả ba bảng, không phụ thuộc sửa code cho từng ngân hàng.
2. Mỗi hàng và ô nguồn có kết quả rõ: đã ánh xạ, cấu trúc, bằng chứng kiểm tra, không quan sát được sau tìm kiếm đầy đủ, không áp dụng có chứng cứ, hoặc chưa giải quyết. Không giấu hàng bị rơi và không biến lỗi thuật toán thành nguồn không có dữ liệu.
3. Đúng statement, entity, phạm vi riêng hoặc hợp nhất, kỳ, cột so sánh, đơn vị và dấu. Có kiểm tra kế toán nhưng không dùng phương trình để sáng tạo số nguồn.
4. Focused tests, kiểm thử chống sửa bằng chứng, đối chiếu corpus chính và corpus kiểm chứng, lưu SQLite, đọc lại, kiểm tra database và kiểm chứng nguồn đều đạt. Chỉ số tốc độ được đo cùng khối lượng đọc, không đánh đổi độ chính xác lấy tốc độ.
5. Excel giữ đúng schema và thứ tự template; mở lại kiểm tra **giá trị, trạng thái, đơn vị, kỳ và nguồn từng ô**, không chỉ kiểm tra tên dòng. Không mất chính xác khi chuyển sang số Excel.
6. Có ledger, giới hạn còn lại, test receipts, commit và artifact keys để Codex review và tích hợp.

Có thể nghiệm thu độc lập workbook **PRIMARY_ONLY** khi ba bảng đạt các gate của chúng; không cần đợi TM hoàn tất. Workbook đó phải ghi rõ chưa bao gồm thuyết minh, không được tự nhận là toàn bộ sản phẩm BCTC đã hoàn thành và không gán NOT_OBSERVED cho các family TM chưa làm.

Ưu tiên một lát cắt hoàn chỉnh đi từ nguồn đến Excel có kiểm chứng, sau đó mở rộng độ phủ. Không dừng ở thiết kế, classifier hoặc các ví dụ chọn riêng dễ xử lý.
