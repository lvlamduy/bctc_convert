# Family 2 — Tiền gửi tại Ngân hàng Nhà nước

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng mới. Đây là trạng
thái trung gian để tiếp tục sửa thuật toán và nhập vào ledger cuối sau replay
đủ 271 PDF.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 62 | 115 | +53 |
| NOT_OBSERVED | 9 | 52 | +43 |
| UNRESOLVED | 133 | 37 | -96 |

- Kiểm tra tổng: **115 READY + 52 NOT_OBSERVED + 37 UNRESOLVED = 204 PDF**.
- Kết quả có **363 mapping**.
- Hai PDF BVB trước đây bị ghi NOT_OBSERVED đã được kiểm tra lại: PDF có bảng
  VND/ngoại tệ và tổng khớp, nên đã chuyển sang READY. Đây là sửa false-N có
  bằng chứng, không phải mở rộng alias tùy tiện.
- 37 trường hợp dưới đây được tách rõ thành khoảng trống thuật toán, dòng nguồn
  khác bản chất schema, và thiếu ID thật. Không coi tất cả là lỗi schema.

## Tiến độ theo ngân hàng

| Ngân hàng | PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED |
|---|---:|---:|---:|---:|
| ABB | 7 | 2 | 5 | 0 |
| BAB | 5 | 1 | 0 | 4 |
| BVB | 8 | 7 | 0 | 1 |
| EIB | 13 | 3 | 10 | 0 |
| KLB | 11 | 9 | 0 | 2 |
| LPB | 6 | 6 | 0 | 0 |
| MSB | 13 | 13 | 0 | 0 |
| NAB | 11 | 1 | 10 | 0 |
| NVB | 8 | 5 | 0 | 3 |
| OCB | 13 | 3 | 10 | 0 |
| PGB | 7 | 7 | 0 | 0 |
| SGB | 12 | 0 | 0 | 12 |
| SHB | 14 | 12 | 2 | 0 |
| SSB | 13 | 13 | 0 | 0 |
| STB | 13 | 3 | 10 | 0 |
| TCB | 16 | 16 | 0 | 0 |
| TPB | 10 | 10 | 0 | 0 |
| VAB | 13 | 0 | 0 | 13 |
| VBB | 11 | 4 | 5 | 2 |
| **Tổng** | **204** | **115** | **52** | **37** |

## Cấu trúc schema đã nhận diện

| Khoản mục | ReportNormId | Cách dùng |
|---|---:|---|
| Tiền gửi tại Ngân hàng Nhà nước | 569 | Root/control của family |
| Tiền gửi tại NHNN Việt Nam | 570 | Parent nhóm Việt Nam |
| Bằng VND | 571 | Mapping trực tiếp |
| Bằng ngoại tệ | 572 | Mapping trực tiếp; không bao gồm vàng |
| Tiền gửi phong tỏa | 573 | Mapping trực tiếp khi nguồn ghi đúng bản chất |
| Tiền gửi tại NHTW khác | 574 | Tổng hợp đúng các vai trò Lào/Campuchia khi nguồn tách |

Các biến thể `Tiền gửi thanh toán tại NHNN`, VND/ngoại tệ lồng dưới parent Việt
Nam, hoặc parent bị mất trong JSON phải được xử lý bằng hierarchy và phương
trình chung; không routing theo ngân hàng hay số trang.

## 37 PDF còn UNRESOLVED

Không hồ sơ nào dưới đây được ép dòng `vàng và ngoại tệ` vào ReportNormId 572,
vì 572 chỉ biểu diễn ngoại tệ.

| # | Ngân hàng | File PDF | Trang PDF | Nội dung thực tế | Schema gần nhất | Kết luận |
|---:|---|---|---:|---|---|---|
| 1 | BAB | `1_bab_2026_2_4_4d13ce7_vi_baocaotaichinh_q4_2025.pdf` | 21 | `Tiền gửi thanh toán tại NHNN`; dòng phong tỏa rỗng; tổng | 570/573/569 | **KHOẢNG TRỐNG THUẬT TOÁN** — cần hỗ trợ một dòng có giá trị + tổng và giữ ô trống, không suy ra zero. |
| 2 | BAB | `BAB_BCTC Hop nhat Quy 3.2025_Tieng Viet.pdf` | 20 | `Tiền gửi thanh toán tại NHNN` + tổng | 570/569 | **KHOẢNG TRỐNG THUẬT TOÁN** — nguồn rõ và schema có vai trò gần đúng. |
| 3 | BAB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | 20 | `Tiền gửi thanh toán tại NHNN` + tổng | 570/569 | **KHOẢNG TRỐNG THUẬT TOÁN** — không được giữ U chỉ do engine đòi 2–3 vai trò. |
| 4 | BAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 20 | `Tiền gửi thanh toán tại NHNN` + tổng | 570/569 | **KHOẢNG TRỐNG THUẬT TOÁN**. |
| 5 | BVB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | 23 | VND + ngoại tệ + `Tiền gửi khác` có giá trị; tổng gồm cả ba | 571/572; chưa có ID cho `Tiền gửi khác` | **CHƯA CÓ TRONG SCHEMA** — không thể bỏ dòng có giá trị hoặc ép vào tiền gửi phong tỏa. |
| 6 | KLB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 29 | VND + ngoại tệ + tổng khớp | 571/572/569 | **CHƯA XÁC ĐỊNH ĐƯỢC ĐƠN VỊ** — cần audit khả năng kế thừa unit cấp tài liệu; không đoán scale. |
| 7 | KLB | `VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf` | 26 | VND + ngoại tệ + tổng khớp | 571/572/569 | **CHƯA XÁC ĐỊNH ĐƯỢC ĐƠN VỊ** — không phải thiếu schema. |
| 8 | NVB | `6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf` | 29 | Nhóm Việt Nam; VND/ngoại tệ có số; tổng khớp | 570/571/572/569 | **KHOẢNG TRỐNG THUẬT TOÁN** — JSON làm phẳng hierarchy; cần khôi phục quan hệ cha/con bằng owner và phép cộng. |
| 9 | NVB | `BCTC Công ty mẹ quý 1 năm 2025.pdf` | 28 | Cùng cấu trúc | 570/571/572/569 | **KHOẢNG TRỐNG THUẬT TOÁN** — PDF đủ, không phải lỗi schema. |
| 10 | NVB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | 28 | Cùng cấu trúc | 570/571/572/569 | **KHOẢNG TRỐNG THUẬT TOÁN**. |
| 11 | SGB | `BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf` | 23 | VND + `Bằng vàng và ngoại tệ` + tổng | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. Có thể map riêng phần VND nhưng không tách dòng gộp. |
| 12 | SGB | `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf` | 23 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 13 | SGB | `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf` | 22 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 14 | SGB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | 20 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 15 | SGB | `BCTC-hop-nhat-da-duoc-kiem-toan-2025.pdf` | 26 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 16 | SGB | `BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf` | 26 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 17 | SGB | `BCTCBNHN.pdf` | 27 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 18 | SGB | `BCTCBNRL.pdf` | 27 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 19 | SGB | `5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf` | 22 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 20 | SGB | `7_sgb_2026_7_27_a0f7e4f_vi__bao_cao_tai_chinh_q22026_daky.pdf` | 21 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 21 | SGB | `BCTC-HN-quy-1---2026_VIE_0001.pdf` | 23 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 22 | SGB | `BCTC-Rieng-le-quy-1---2026_VIE.pdf` | 22 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 23 | VAB | `20250815 - VAB - BCTC HN BAN NIEN 2025_0001.pdf` | 28 | VND + `Bằng vàng và ngoại tệ` + tổng | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 24 | VAB | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | 28 | Dòng gộp vàng/ngoại tệ; local unit thiếu | 571; 572 chỉ gần nghĩa | **DÒNG GỘP KHÁC BẢN CHẤT + THIẾU UNIT EXACT**. |
| 25 | VAB | `2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf` | 27 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **DÒNG GỘP KHÁC BẢN CHẤT + THIẾU UNIT EXACT**. |
| 26 | VAB | `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | 29 | VND + dòng gộp + tổng | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 27 | VAB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | 29 | Cùng mẫu; unit không có trong JSON bảng | 571; 572 chỉ gần nghĩa | **DÒNG GỘP KHÁC BẢN CHẤT + THIẾU UNIT EXACT**. |
| 28 | VAB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | 29 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **DÒNG GỘP KHÁC BẢN CHẤT + THIẾU UNIT EXACT**. |
| 29 | VAB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 29 | VND + dòng gộp + tổng | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 30 | VAB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | 30 | Cùng mẫu; continuation | 571; 572 chỉ gần nghĩa | **DÒNG GỘP KHÁC BẢN CHẤT + KHOẢNG TRỐNG CONTINUATION**. |
| 31 | VAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 30 | Cùng mẫu; continuation | 571; 572 chỉ gần nghĩa | **DÒNG GỘP KHÁC BẢN CHẤT + KHOẢNG TRỐNG CONTINUATION**. |
| 32 | VAB | `BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf` | 27 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 33 | VAB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | 30 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 34 | VAB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | 30 | Cùng mẫu | 571; 572 chỉ gần nghĩa | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 35 | VAB | `BCTC Q1.2026 RIENG LE_0001.pdf` | 29–30 | p29 có parent + VND; p30 có dòng gộp + tổng | 571; 572 chỉ gần nghĩa | **KHOẢNG TRỐNG CHỌN/GHÉP TRANG + DÒNG GỘP KHÁC BẢN CHẤT**; PDF đầy đủ. |
| 36 | VBB | `000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf` | 15 | VND + ngoại tệ + phong tỏa + `Tiền gửi khác` rỗng + tổng | 571/572/573 | **KHOẢNG TRỐNG THUẬT TOÁN** — dòng rỗng phải được bảo toàn nhưng không được chặn các mapping có số. |
| 37 | VBB | `1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf` | 14 | Cùng mẫu | 571/572/573 | **KHOẢNG TRỐNG THUẬT TOÁN** — không suy ô trống thành zero và không biến nó thành lỗi schema có giá trị. |

## Tổng hợp nguyên nhân và việc còn phải làm

| Nhóm | Số PDF | Xử lý đúng |
|---|---:|---|
| Dòng gộp vàng + ngoại tệ | 25 | Giữ dòng gộp là SOURCE_ONLY khác bản chất; vẫn map riêng các dòng thật sự có ID nếu closure cho phép |
| Closure một dòng + tổng | 4 | Sửa thuật toán generic; không phải schema gap |
| JSON làm phẳng parent/child | 3 | Khôi phục hierarchy bằng owner + phép cộng có receipt |
| Thiếu unit cục bộ | 2 | Visual-audit unit cấp trang/tài liệu; chỉ kế thừa khi có bằng chứng duy nhất |
| Dòng `Tiền gửi khác` rỗng | 2 | Bảo toàn blank, không suy zero, không chặn mapping khác |
| `Tiền gửi khác` có giá trị | 1 | Schema gap thật; cần đánh giá có tạo ID mới hay không |

## SOURCE_ONLY / CONTROL trong PDF READY

Dòng tổng và parent được giữ làm control phương trình, không tạo mapping trùng.
Tại checkpoint này không có ITEM có giá trị, cùng bản chất với ReportNormId hiện
hữu, bị bỏ lại trong 115 PDF READY. Các dòng gộp vàng + ngoại tệ nằm trong nhóm
UNRESOLVED ở trên và phải được xử lý theo chính sách partial mapping trước khi
chốt family.

## NOT_OBSERVED

52 PDF không có family này trong đúng phạm vi báo cáo đã kiểm tra. Phân bố theo
ngân hàng đã ghi ở bảng tiến độ. Danh sách file chi tiết sẽ được sinh từ replay
đủ 271 PDF vào ledger cuối.

## Truy vết kỹ thuật

- Kết quả audit: `/dev/shm/family02-audit-rerun-v3.json`
- Database replay: `/dev/shm/family02-audit-rerun-v3.sqlite3`
- Audit residual gốc: `/dev/shm/family02-residual-human-audit-v1.md`
