# Thuật toán số hóa thuyết minh BCTC ngân hàng: rà soát và kiến trúc đề xuất (v1)

Trạng thái: tài liệu thiết kế cho nhánh pilot `claude/tm-notes-next`. Tài liệu này không phải nghiệm thu tài chính. Mọi con số dẫn ra đều là quan sát ở mức development diagnostic.

## 1. Chẩn đoán cách làm cũ

Các family TM (F8, F15, F36, F37, F39, …) hiện chạy chung một evaluator đa bảng đã bị đóng băng (frozen). Mỗi family sửa lỗi bằng logic recovery cục bộ. Cách làm này có ba nhược điểm:

1. **Thay đổi lan sang mọi family.** Một sửa đổi trong evaluator chung buộc phải kiểm lại toàn bộ family. Ngược lại, recovery cục bộ thì nhân bản dần những cách xử lý gần giống nhau.
2. **Nhận diện bằng tổ hợp.** Cách tìm bảng là ghép 2 khoản mục, nếu trùng thì tăng lên 3, rồi thêm biến thể header, biến thể trình bày, sang trang, kỳ, lũy kế… Số biến thể tăng theo cấp số nhân, và một bảng lạ vẫn có thể "khớp" nhờ trùng ngẫu nhiên.
3. **Chọn bằng số liệu.** Dùng sự trùng số với PRIMARY hay phương trình để quyết định kỳ, đơn vị hay vai trò của dòng là backsolving. Cách này không kiểm chứng được và dễ sai mà không ai biết.

## 2. Kiến trúc mới: kernel dùng chung + shape + plugin YAML

```
src/bctc_ai/notes/
  kernel_v1.py            # nguồn đã xác thực, bridge ORIGINAL, identity, unit, kỳ, sang trang
  source_bridge_v1.py     # SQL ⇄ trang ORIGINAL: bằng chứng tọa độ từng ô
  list_shape_v1.py        # LIST_BY_AXIS: hàng = member của trục, cột = kỳ (chất lượng nợ)
  coordinate_shape_v1.py  # COORDINATE_LIST: hai trục (loại tiền gửi × tiền tệ, loại khách hàng)
  concept_list_shape_v1.py# CONCEPT_LIST: dòng của một trục đóng, cột = duration (thuế, chi phí HĐ, dự phòng)
  engine_v1.py            # chạy một family; collision; coverage; dispositions
  store_v1.py, export_v1.py, run_v1.py
config/notes/
  axes_v1.yaml            # các trục và member (từ vựng dùng chung)
  families/<family>_v1.yaml  # plugin: shape, trục, retrieval, subject, phương trình, anchor, luật owner
  crosswalk_v1.yaml       # (concept, axis, member) -> ReportNormId của template cũ
```

- **Kernel (dùng chung, ổn định):**
  - xác thực nguồn: index, DB, manifest, BLOB SHA;
  - bridge ORIGINAL: bảng SQL phải khớp typed-exact với trang gốc, lệch thì loại bảng;
  - bind identity PRIMARY theo document và corpus, không dò theo ordinal;
  - đơn vị theo bằng chứng in ra, có kiểm xung đột với đơn vị mà bảng sở hữu;
  - kỳ theo cửa sổ in ra;
  - ghép bảng sang trang có fence owner;
  - tính phương trình cố định;
  - ô trùng khóa (collision) thì giữ lại;
  - store ghi một lần, reload và rebuild trong process mới phải khớp chính xác.
- **Shape (một vài module):** mỗi shape là một dạng bảng thuyết minh. Shape mới chỉ được thêm khi xuất hiện một dạng trình bày thật sự mới, ví dụ ROLLFORWARD cho bảng biến động. Không thêm shape cho từng ngân hàng.
- **Plugin family (chỉ YAML):** trục dòng, retrieval, subject, `reject_context`, các dòng được emit, phương trình, anchor PRIMARY (chỉ dùng để xác nhận hoặc veto), và các luật `owner`/`scoped`/`not_within`/`transparent_wrappers`.

**Chia để trị:** sửa một family chỉ là sửa file YAML của nó, kèm test của nó. Kernel và shape có test riêng. Mỗi family được pin SHA trong manifest, nên một thay đổi không âm thầm ảnh hưởng family khác.

## 3. Schema so sánh được giữa các ngân hàng (dimensional)

Mỗi ô được lưu theo khóa: `(document, scope, concept, axis, member, classification_basis, period_key)`, kèm `unit`, `observation_state`, `value`, `raw`, `original_cell` (tọa độ gốc VID/s/t/r/c), `acceptance`/`hold_reasons` và `semantic_state`.

- **So sánh giữa ngân hàng:** người dùng chọn một `(concept, axis, member)`, ví dụ `LOANS_TO_CUSTOMERS / CREDIT_QUALITY_GROUP / G3`, rồi so cùng kỳ và cùng scope giữa các ngân hàng.
- **Member chung, alias theo cách trình bày.** Ví dụ G1…G5 nhận cả "Nhóm 1…5" lẫn "Nợ đủ tiêu chuẩn… Nợ có khả năng mất vốn".
- **Member ngoài khung (`outside_members`) cho phần đặc thù nhưng phổ biến.** Ví dụ "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán" của ngân hàng có công ty chứng khoán, hay "Nợ chờ xử lý đã có tài sản gán, xiết nợ". Các member này không làm sai tổng 5 nhóm, và `GRAND_TOTAL` vẫn đối chiếu được.
- **Thêm khoản mục mà không gây phản ứng dây chuyền:** chỉ thêm member vào trục (và nếu cần thì thêm một dòng crosswalk). Family khác và kernel không đổi. Ô không có ReportNormId vẫn được lưu và vẫn so sánh được.
- **Dòng có nghĩa chưa chứng minh** (ví dụ 5729/5730 chưa phân biệt được số gốc với hiệu ứng thuế) không nhận ID cũ. Ô vẫn được giữ, kèm `semantic_state` để người đọc không nhầm.
- **Không lấy đặc thù riêng của từng ngân hàng.** Dòng không thuộc trục được giữ dưới dạng `SOURCE_ONLY`, có đủ tọa độ để audit, nhưng không bị ép vào schema.

## 4. Nhận diện bằng cấu trúc đã chứng minh, không bằng tổ hợp

- **Một dòng thuộc một line** khi nhãn khớp luật của line (`all_of`/`none_of`/`exact`). Khớp nhiều line thì giữ AMBIGUOUS, không chọn. Một line được in hai lần thì cũng giữ lại.
- **Nhãn "trơ"** như "Chi khác" hay "Dự phòng chung" chỉ được đọc dưới một dòng cha **đã chứng minh**: có `parent_row_id` cộng đường dẫn phân cấp gốc, dòng cha duy nhất và in trước. Không đoán theo vị trí hay theo số tiền.
- **Owner:** ví dụ khoản đóng góp theo lương phải nằm dưới dòng "Chi phí cho nhân viên" có vai trò cuối cùng không mơ hồ. Riêng F36 có opt-in đi xuyên đúng một wrapper "Trong đó" mà mọi ô trống thật trong trang gốc.
- **Kỳ:** lấy theo cửa sổ in ra. "Kỳ này/Kỳ trước" không có ngày in ra thì HOLD (DECISIONS #14).
- **Đơn vị:** lấy theo bằng chứng in ra; không suy ra từ độ lớn của số.
- **Chấp nhận một ô** chỉ khi có phương trình cố định PASS, hoặc anchor PRIMARY trùng cùng cửa sổ và cùng đơn vị. Mọi trường hợp khác giữ HOLD kèm lý do.

## 5. Kết quả đo được (development diagnostic, FULL271)

| Lượt | Kết quả |
|---|---|
| Pilot `153912Z` (`220ea3c`) | 31.080 ô; bridge: 0 bảng bị loại; 4 phút 45 giây; RSS 630 MB |
| Pilot `164023Z` (`1fc78cb`, 6 guard) | 30.702 ô. OPEX ACCEPTED từ 2.578 xuống 1.370, do 145 dòng payroll không chứng minh được owner nên phương trình INCOMPLETE. Tách ra được nguyên nhân bằng tọa độ nguồn. |
| Unit `c372c45` | 122/122, gồm sửa nhãn ghép và wrapper |

## 6. Lộ trình

1. Coverage `OBSERVED_UNRESOLVED` (`2752878`), chạy unit, rồi một lượt pilot FULL271 có pin để đo wrapper FULL193 và 12 tài liệu F37.
2. Chỉ thêm luật marker đầu dòng ("- ") cho nhãn và hierarchy sau khi có kế hoạch đọc dữ liệu ORIGINAL đã được duyệt.
3. Khi F36, F37 và F39 đã đóng terminal:
   - CONCEPT_LIST cho thu nhập lãi và chi phí lãi (chỉ thêm config);
   - shape ROLLFORWARD cho biến động dự phòng và TSCĐ.
4. So sánh pilot với F39 theo tọa độ ORIGINAL, chỉ trên các bảng mà bridge của pilot chứng minh là không bị shift.
