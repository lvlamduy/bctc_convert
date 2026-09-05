# Family 8 — Phân tích chất lượng nợ cho vay

Checkpoint này rà soát tập bất biến 204 PDF của 19 ngân hàng mới, chỉ gồm báo cáo từ năm 2025 đến hiện tại và chỉ gồm PDF đã có đủ JSON toàn tài liệu. Đây là bằng chứng staging để tổng hợp vào hai bảng cuối dự án; chưa thay thế `COMPLETED_TM_FAMILIES.md` hoặc `UNRESOLVED_MAPPING_LEDGER.md`.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 151 | 204 | +53 |
| NOT_OBSERVED | 9 | 0 | -9 |
| UNRESOLVED | 44 | 0 | -44 |

- Kiểm tra tổng: **204 READY + 0 NOT_OBSERVED + 0 UNRESOLVED = 204 PDF**.
- Kết quả cuối có **1.235 mapping**. Không PDF nào có ReportNormId trùng và thứ tự mapping giữ đúng thứ tự schema.
- 151 PDF READY cũ đều tiếp tục READY. Trong đó 149 PDF giữ nguyên toàn bộ mapping; hai PDF VAB được sửa một kết quả READY sai có bằng chứng nguồn rõ ràng, trình bày riêng bên dưới.
- Chín PDF KLB từng bị ghi NOT_OBSERVED thực tế đều có bảng đầy đủ. Đây là **false NOT_OBSERVED đã được sửa**, không phải family không xuất hiện.
- Sau audit không còn trường hợp UNRESOLVED. Các dòng nhìn thấy nhưng không có quan hệ một-một với schema được giữ riêng ở mục SOURCE_ONLY, không biến thành lỗi của toàn PDF.

## Tiến độ theo ngân hàng

| Ngân hàng | PDF khảo sát | Baseline READY | Baseline NOT_OBSERVED | Baseline UNRESOLVED | Kết quả cuối READY |
|---|---:|---:|---:|---:|---:|
| ABB | 7 | 7 | 0 | 0 | 7 |
| BAB | 5 | 5 | 0 | 0 | 5 |
| BVB | 8 | 0 | 0 | 8 | 8 |
| EIB | 13 | 13 | 0 | 0 | 13 |
| KLB | 11 | 2 | 9 | 0 | 11 |
| LPB | 6 | 2 | 0 | 4 | 6 |
| MSB | 13 | 13 | 0 | 0 | 13 |
| NAB | 11 | 11 | 0 | 0 | 11 |
| NVB | 8 | 8 | 0 | 0 | 8 |
| OCB | 13 | 0 | 0 | 13 | 13 |
| PGB | 7 | 7 | 0 | 0 | 7 |
| SGB | 12 | 12 | 0 | 0 | 12 |
| SHB | 14 | 8 | 0 | 6 | 14 |
| SSB | 13 | 13 | 0 | 0 | 13 |
| STB | 13 | 12 | 0 | 1 | 13 |
| TCB | 16 | 9 | 0 | 7 | 16 |
| TPB | 10 | 8 | 0 | 2 | 10 |
| VAB | 13 | 12 | 0 | 1 | 13 |
| VBB | 11 | 9 | 0 | 2 | 11 |
| **Tổng** | **204** | **151** | **9** | **44** | **204** |

## Cấu trúc schema đã nhận diện

ReportNormId 716 là owner “Cho vay khách hàng”. Family 8 nhận diện tổng phân tích chất lượng và năm nhóm nợ. Khoản cho vay ký quỹ/ứng trước tiền bán chứng khoán chỉ được map khi PDF thực sự trình bày nó như một cấu phần cộng riêng.

| Khoản mục schema | ReportNormId | Số PDF READY có mapping |
|---|---:|---:|
| Phân tích chất lượng nợ cho vay | 746 | 204 |
| Nợ đủ tiêu chuẩn | 747 | 204 |
| Nợ cần chú ý | 748 | 204 |
| Nợ dưới tiêu chuẩn | 749 | 204 |
| Nợ nghi ngờ | 750 | 204 |
| Nợ có khả năng mất vốn | 751 | 204 |
| Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán | 1944 | 11 |

“Nợ đủ tiêu chuẩn” có thể là một dòng trực tiếp hoặc được cộng từ nợ đủ tiêu chuẩn cốt lõi với một cấu phần được trình bày riêng, chẳng hạn nghiệp vụ thư tín dụng trả chậm. Đây là phép cộng có chứng minh số học, không phải tạo khoản mục mới.

Các biến thể đã xử lý:

- `Nhóm 1- Nợ đủ tiêu chuẩn` và các nhóm 2–5 có dấu gạch nối dính sát số nhóm được coi là cùng nhãn với biến thể có khoảng trắng.
- `Các khoản cho vay hoạt động ký quỹ và cho vay hoạt động ứng trước tiền bán của khách hàng` là alias của ReportNormId 1944, không tạo ID mới chỉ vì cách gọi khác.
- `Số cuối quý` và `Số đầu năm` được giữ nguyên làm header kỳ hiện tại/kỳ so sánh. Hệ thống không bịa ngày cuối quý khi PDF chỉ ghi vai trò kỳ.
- Một bảng “Cho vay khách hàng” rộng chỉ được cắt tới nhóm “Phân tích chất lượng nợ cho vay” khi có đúng một group cha cụ thể, các hàng con liên tục, không rò sang sibling và số học khép kín.
- Một bảng bị tách qua hai trang chỉ được ghép khi hai trang liền kề khai báo đúng hướng tiếp nối, cột tương thích và toàn bộ năm nhóm cộng khớp dòng tổng.

## Chín PDF KLB từng bị ghi sai là NOT_OBSERVED

Cả chín PDF đều có đủ năm nhóm nợ, hai kỳ và dòng tổng. Từng cột đều thỏa `Nhóm 1 + Nhóm 2 + Nhóm 3 + Nhóm 4 + Nhóm 5 = Tổng`. Nguyên nhân bỏ sót là cách viết `Nhóm 1- Nợ...`, không phải thiếu source hoặc thiếu schema.

| # | File PDF | Kỳ / báo cáo | Trang PDF | Tổng kỳ hiện tại / kỳ so sánh |
|---:|---|---|---:|---:|
| 1 | `BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf` | Q3/2025, hợp nhất, kiểm toán: chưa xác định | 21 | 70.922.390 / 61.431.909 triệu đồng |
| 2 | `BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf` | Q3/2025, công ty mẹ, kiểm toán: chưa xác định | 22 | 70.922.390 / 61.431.909 triệu đồng |
| 3 | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ, kiểm toán: chưa xác định | 21 | 69.547.023 / 61.431.909 triệu đồng |
| 4 | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất, kiểm toán: chưa xác định | 20 | 69.547.023 / 61.431.909 triệu đồng |
| 5 | `bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_tv.pdf` | Q4/2025, hợp nhất, kiểm toán: chưa xác định | 22 | 71.587.702 / 61.431.909 triệu đồng |
| 6 | `bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf` | Q4/2025, công ty mẹ, kiểm toán: chưa xác định | 23 | 71.587.702 / 61.431.909 triệu đồng |
| 7 | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ, kiểm toán: chưa xác định | 26 | 73.234.993 / 71.587.702 triệu đồng |
| 8 | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ, kiểm toán: chưa xác định | 26 | 77.617.866 / 71.587.702 triệu đồng |
| 9 | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất, kiểm toán: chưa xác định | 26 | 73.234.993 / 71.587.702 triệu đồng |

Kết luận: cả chín trường hợp chuyển **NOT_OBSERVED → READY**. Hai bảng KLB nằm trong một bảng thuyết minh rộng còn phải qua thêm điều kiện cắt đúng subtree; các sibling ngoài nhóm chất lượng nợ không được kéo vào mapping.

## Sáu PDF SHB có hai bảng cùng năm nhóm nhưng khác phạm vi

SHB trình bày cả bảng 10.4 và bảng 10.5 “theo TT31/2024/TT-NHNN”. Hai bảng đều tự khép số học nên baseline báo MULTIPLE. Tuy nhiên, bảng 10.4 có tổng khớp chính xác với “Cho vay khách hàng” và các bảng 10.1/10.2/10.3; bảng 10.5 có phạm vi quy định rộng hơn và tổng lớn hơn. Vì ReportNormId 746 thuộc owner 716 “Cho vay khách hàng”, bảng 10.4 là nguồn mapping đúng.

| File PDF | Kỳ / báo cáo | Trang PDF | Tổng bảng 10.4 được map | Tổng bảng 10.5 theo TT31, SOURCE_ONLY |
|---|---|---:|---:|---:|
| `20260130 - SHB - Bao cao tai chinh Q4.2025 Rieng le.pdf` | Q4/2025, công ty mẹ, kiểm toán: chưa xác định | 26 | 601.422.252 / 508.719.989 | 734.347.843 / 635.884.979 |
| `BCTC Công ty mẹ quý 1 năm 2025.pdf` | Q1/2025, công ty mẹ, kiểm toán: chưa xác định | 25 | 554.243.439 / 506.112.656 | 677.177.312 / 635.884.979 |
| `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ, kiểm toán: chưa xác định | 25 | 580.780.481 / 506.112.656 | 682.309.646 / 635.884.979 |
| `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất, kiểm toán: chưa xác định | 25–26 | 567.948.143 / 519.949.991 | 691.566.059 / 650.343.835 |
| `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất, kiểm toán: chưa xác định | 25–26 | 594.564.116 / 519.949.991 | 696.691.225 / 650.343.835 |
| `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất, kiểm toán: chưa xác định | 27 | 614.861.980 / 522.557.324 | 748.752.548 / 650.343.835 |

Phân loại bảng 10.5: **CÓ ID GẦN NGHĨA NHƯNG KHÁC PHẠM VI**. Đây không phải “chưa có schema” và cũng không phải lỗi source/OCR. Bảng được giữ để con người kiểm tra nhưng không dùng thay cho bảng chất lượng của “Cho vay khách hàng”.

## Bốn PDF LPB có hai bảng ngang theo từng kỳ

LPB đặt ngày ở một câu dẫn ngay trước hai bảng, thay vì lặp lại ngày trong header từng bảng. Hệ thống chỉ gắn kỳ theo thứ tự nguồn khi có đúng một câu dẫn chứa đúng hai ngày đầy đủ, kỳ hiện tại đứng trước kỳ so sánh trong ngoặc; đúng hai bảng; cấu trúc cột/hàng giống nhau; không bảng nào có ngày riêng; và cả hai bảng đều tự khép số học.

| File PDF | Kỳ / báo cáo | Trang PDF | Hai ngày đọc trực tiếp từ câu dẫn | Tổng RNID 746 |
|---|---|---:|---|---:|
| `BCTC 31.12.2025 VN color.pdf` | 31/12/2025; phạm vi/kiểm toán: chưa xác định | 81 | 31/12/2025 và 31/12/2024 | 391.746.491 / 331.606.315 |
| `BCTC Q3.2025 VN.pdf` | Q3/2025; phạm vi/kiểm toán: chưa xác định | 80 | 30/09/2025 và 31/12/2024 | 387.897.531 / 331.606.315 |
| `BCTC quý 1 năm 2025.pdf` | Q1/2025; phạm vi/kiểm toán: chưa xác định | 77 | 31/03/2025 và 31/12/2024 | 352.194.088 / 331.606.315 |
| `BCTC quý 2 năm 2026.pdf` | Q2/2026; phạm vi/kiểm toán: chưa xác định | 79 | 30/06/2026 và 31/12/2025 | 429.464.738 / 391.746.491 |

Các trường hợp chỉ có một ngày, hơn hai ngày, ngày đảo ngược/trùng nhau, một bảng có ngày riêng, hơn hai bảng, header khác nhau hoặc số học không khép đều bị chặn trong test. Không dùng năm đơn lẻ để suy ra ngày cuối kỳ.

## Các trường hợp còn lại đã chuyển UNRESOLVED → READY

- **TCB (7 PDF) và TPB (2 PDF):** dòng “Các khoản cho vay hoạt động ký quỹ và cho vay hoạt động ứng trước tiền bán của khách hàng” là alias đúng bản chất và được map vào 1944. Tính cả hai PDF vốn đã READY, kết quả cuối có 11 PDF map 1944.
- **STB (1 PDF):** `BCTC Hợp nhất quý 1 năm 2025.pdf`, trang 31 có một group “Phân tích chất lượng nợ cho vay” duy nhất trong bảng rộng; năm hàng con và tổng khép chính xác. Chỉ subtree này được dùng.
- **VAB (1 PDF):** `BCTC Hợp nhất quý 2 năm 2026.pdf`, trang 32–33. Trang 32 có bốn nhóm đầu và khai báo tiếp sang trang sau; trang 33 có nhóm 5 cùng dòng tổng. Hai trang được ghép đúng thứ tự và khép chính xác.
- **VBB (2 PDF):** `000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf`, trang 16 và `1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf`, trang 15. Header nguồn là “Số cuối quý / Số đầu năm”; mapping giữ nguyên hai nhãn đó, không tự tạo ngày.

## Hai kết quả VAB READY cũ được sửa vì đã chọn nhầm family

Đây là hai thay đổi có bằng chứng mới, không phải READY regression. Baseline chọn bảng “Phân tích chất lượng dư nợ của hoạt động mua nợ”; toàn bộ số đều là dấu gạch nên bị diễn giải thành 0. PDF đồng thời có bảng explicit “Phân tích chất lượng nợ cho vay” với số khác 0 và tổng khép chính xác.

| File PDF | Nguồn cũ bị chọn nhầm | Mapping cũ | Nguồn đúng sau audit | Mapping RNID 746 sau audit |
|---|---|---:|---|---:|
| `BCTC Công ty mẹ quý 3 năm 2025.pdf` | Trang 34, chất lượng **hoạt động mua nợ** | 0 / 0 | Trang 31–32, chất lượng **nợ cho vay** | 86.830.861 / 79.915.536 |
| `BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf` | Trang 32, chất lượng **hoạt động mua nợ** | 0 / 0 | Trang 29–30, chất lượng **nợ cho vay** | 87.421.681 / 79.915.536 |

Hai bảng đúng đều là continuation hai trang. Các mapping 747–751 cũng đổi từ toàn 0 sang đúng năm nhóm nhìn thấy trên bảng; không dùng backsolve từ báo cáo khác.

## SOURCE_ONLY trong PDF READY — 21 dòng cộng vào tổng nhưng chưa có ID một-một

BVB và OCB có một hàng thứ sáu ngoài năm nhóm nợ:

> “Các khoản nợ chờ xử lý đã có tài sản xiết/gán nợ và nợ tồn đọng có tài sản bảo đảm/đảm bảo”.

Trong cả 21 PDF, năm nhóm nợ cộng thêm hàng này bằng đúng dòng tổng ở cả hai kỳ. Vì vậy hàng được giữ làm bằng chứng khép tổng, còn RNID 746–751 vẫn map chính xác. Tuy nhiên:

- ReportNormId 724 “Nợ cho vay được khoanh và nợ chờ xử lý” nằm dưới family sibling 717 và có phạm vi rộng/khác với hàng bị ràng buộc thêm điều kiện tài sản xiết/gán nợ.
- ReportNormId 993 “Tài sản gán nợ chờ xử lý” là một khoản mục tài sản khác, khác bản chất khoản nợ cho vay.
- Không được ép hàng này vào 724 hoặc 993. Nếu nghiệp vụ yêu cầu lưu riêng, cần đánh giá có tạo child mới dưới 746 hay không.

Phân loại chung: **CÓ ID GẦN NGHĨA NHƯNG KHÁC PHẠM VI/BẢN CHẤT** và **KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG**.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang PDF | Tên khoản mục thực tế | Giá trị hai cột theo PDF |
|---:|---|---|---|---:|---|---:|
| 1 | BVB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | Q4/2025, công ty mẹ, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 70.319 / 82.170 triệu VND |
| 2 | BVB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | – / 82.170 triệu VND |
| 3 | BVB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 70.319 / 82.170 triệu VND |
| 4 | BVB | `VI_BaoCaoTaiChinhHopNhat_Kiemtoan_2025.pdf` | Năm 2025, hợp nhất, kiểm toán | 37 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 70.319 / 82.170 triệu đồng |
| 5 | BVB | `VI_BaoCaoTaiChinhRiengLe_Kiemtoan_2025.pdf` | Năm 2025, riêng lẻ, kiểm toán | 36 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 70.319 / 82.170 triệu đồng |
| 6 | BVB | `VI_BaoCaoTaiChinhRiengLe_Q2_2025.pdf` | Q2/2025, riêng lẻ, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 74.176 / 82.170 triệu VND |
| 7 | BVB | `VI_BaoCaoTaiChinhRiengLe_Q3_2025.pdf` | Q3/2025, riêng lẻ, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 70.685 / 82.170 triệu VND |
| 8 | BVB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất, kiểm toán: chưa xác định | 25 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 65.559 / 70.319 triệu VND |
| 9 | OCB | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 6 tháng/2025, công ty mẹ, soát xét | 43 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản đảm bảo | 1.362.229.337.393 / 1.462.490.542.762 VND |
| 10 | OCB | `BCTC Công ty mẹ quý 1 năm 2025.pdf` | Q1/2025, công ty mẹ, kiểm toán: chưa xác định | 22 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.139.053.129.966 / 1.462.490.542.762 VND |
| 11 | OCB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ, kiểm toán: chưa xác định | 22 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.362.229.337.393 / 1.462.490.542.762 VND |
| 12 | OCB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | Q3/2025, công ty mẹ, kiểm toán: chưa xác định | 22 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.259.443.069.083 / 1.462.490.542.762 VND |
| 13 | OCB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | Năm 2025, hợp nhất, kiểm toán | 43 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 400.724.200.374 / 1.462.490.542.762 VND |
| 14 | OCB | `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 6 tháng/2025, hợp nhất, soát xét | 42 | Các khoản nợ chờ xử lý đã có tài sản xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.362.229.337.393 / 1.462.490.542.762 VND |
| 15 | OCB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.139.053.129.966 / 1.462.490.542.762 VND |
| 16 | OCB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.362.229.337.393 / 1.462.490.542.762 VND |
| 17 | OCB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 1.259.443.069.083 / 1.462.490.542.762 VND |
| 18 | OCB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất, kiểm toán: chưa xác định | 24 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 400.724.200.374 / 1.462.490.542.762 VND |
| 19 | OCB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 341.590.078.226 / 400.724.200.374 VND |
| 20 | OCB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất, kiểm toán: chưa xác định | 23 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 341.590.078.226 / 400.724.200.374 VND |
| 21 | OCB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất, kiểm toán: chưa xác định | 24 | Các khoản nợ chờ xử lý đã có tài sản gán xiết nợ, gán nợ và nợ tồn đọng có tài sản bảo đảm | 330.372.989.092 / 400.724.200.374 VND |

Trong 18 PDF, giá trị hàng này trùng một hàng gần nghĩa ở bảng phân loại theo loại hình cho vay; một BVB là tương đương dấu gạch với ô trống. Nhưng hai PDF OCB Q3/2025 chứng minh không thể coi hai nhãn là alias tuyệt đối: hàng ngắn là 1.260.408.219.083 VND, trong khi hàng dài ở bảng chất lượng chỉ là 1.259.443.069.083 VND, chênh 965.150.000 VND. Vì vậy không ép map vào 724.

## Phân biệt trạng thái ở checkpoint này

| Nhóm | Số PDF / trường hợp | Kết luận |
|---|---:|---|
| READY | 204 PDF | Cấu trúc, kỳ, đơn vị và phép cộng family đều xác định chắc chắn. |
| NOT_OBSERVED | 0 PDF | Chín kết luận vắng mặt cũ đã được chứng minh là false NOT_OBSERVED. |
| UNRESOLVED | 0 PDF | Không còn PDF có cấu trúc family chưa giải được trong tập 204. |
| SOURCE_ONLY — hàng chưa có ID một-một | 21 hàng | Hàng BVB/OCB tham gia khép tổng nhưng không bị ép vào ID gần nghĩa. |
| SOURCE_ONLY — bảng khác phạm vi | 6 bảng | Bảng SHB theo TT31 rộng hơn owner “Cho vay khách hàng”, được giữ để kiểm tra nhưng không map 746–751. |

`STANDARD_CORE` không được tính là khoản mục chưa map: đó là nguồn trực tiếp để tạo đúng mapping 747 “Nợ đủ tiêu chuẩn”. Tương tự, 11 dòng cho vay ký quỹ/ứng trước đã map vào 1944 nên không nằm trong SOURCE_ONLY.

Kiểm tra trùng: 21 hàng BVB/OCB là 21 khóa duy nhất theo ngân hàng + file + trang + nhãn; sáu bảng SHB cũng là sáu khóa file + trang riêng, không trùng ledger.

## Kiểm tra hồi quy

- Bộ 19 ngân hàng mới: 204 READY, 0 NOT_OBSERVED, 0 UNRESOLVED, 1.235 mapping.
- Bộ 8 ngân hàng cũ với đúng lớp sửa source bất biến: 140/140 READY và 867 mapping; trạng thái, mapping và số candidate của cả 140 PDF giống hoàn toàn checkpoint chính thức cũ.
- Family 7 sau thay đổi dùng chung: kết quả byte-identical với checkpoint đã chốt, vẫn 112 READY / 89 NOT_OBSERVED / 3 UNRESOLVED và 1.946 mapping.
- Unit test liên quan Family 7/8, ghép trang và runner: **48 test đạt**. Ruff đạt.

## Truy vết kỹ thuật ở cuối tài liệu

- Baseline 19 ngân hàng: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-08-loan-quality-classification.json`
- Kết quả audit cuối: `/dev/shm/family08-audit-rerun-v5.json`
- Database replay cuối: `/dev/shm/family08-audit-rerun-v5.sqlite3`
- Tập PDF bất biến: `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
- Hồi quy 8 ngân hàng cũ: `/dev/shm/family08-old8-current-regression-v3.json`
- Hồi quy Family 7: `/dev/shm/family07-after-f8-regression-v1.json`
- SHA kết quả Family 8 cuối: `48a61d00c0e69e20f921d43cbe6f3cc9e28d07eec2e0e0d4fc6a247b253f56f8`
