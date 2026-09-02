# Tiến độ Gemini của 19 ngân hàng mới

Checkpoint: **17:35 UTC ngày 02/09/2026**.

## Phạm vi được tính

- Chỉ tính báo cáo từ **Quý 1/2025 đến thời điểm hiện tại**.
- Gồm **212 PDF kỳ 2025 và 67 PDF kỳ 2026**, tổng cộng **279 PDF / 15.335
  trang tiếng Việt**.
- Số PDF kỳ 2024 trong hàng đợi này là **0**. Ngày `31/12/2024` nếu xuất hiện
  chỉ là cột so sánh trong báo cáo 2025/2026.
- Không tính ACB, BID, CTG, HDB, MBB, VCB, VIB và VPB vì tám ngân hàng này đã
  có Gemini JSON và chỉ được tái sử dụng, không gửi lại.

## Tiến độ theo ngân hàng

| Mã ngân hàng | PDF | Trang tiếng Việt | Trang JSON hợp lệ | Hoàn thành theo trang | PDF đã bắt đầu | PDF hoàn tất | PDF cần retry | PDF chờ sửa trang lỗi | PDF chưa bắt đầu |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ABB | 13 | 481 | 434 | 90,23% | 13 | 1 | 0 | 12 | 0 |
| BAB | 12 | 542 | 511 | 94,28% | 12 | 2 | 0 | 10 | 0 |
| BVB | 14 | 742 | 571 | 76,95% | 14 | 1 | 0 | 13 | 0 |
| EIB | 16 | 703 | 687 | 97,72% | 16 | 7 | 0 | 9 | 0 |
| KLB | 18 | 757 | 731 | 96,57% | 18 | 3 | 5 | 10 | 0 |
| LPB | 8 | 702 | 692 | 98,58% | 8 | 2 | 6 | 0 | 0 |
| MSB | 16 | 998 | 981 | 98,30% | 16 | 8 | 6 | 2 | 0 |
| NAB | 16 | 853 | 818 | 95,90% | 16 | 8 | 6 | 2 | 0 |
| NVB | 16 | 864 | 787 | 91,09% | 16 | 5 | 9 | 2 | 0 |
| OCB | 16 | 899 | 74 | 8,23% | 1 | 0 | 0 | 1 | 15 |
| PGB | 7 | 357 | 0 | 0,00% | 0 | 0 | 0 | 0 | 7 |
| SGB | 14 | 703 | 0 | 0,00% | 0 | 0 | 0 | 0 | 14 |
| SHB | 16 | 729 | 0 | 0,00% | 0 | 0 | 0 | 0 | 16 |
| SSB | 16 | 1.063 | 0 | 0,00% | 0 | 0 | 0 | 0 | 16 |
| STB | 16 | 972 | 0 | 0,00% | 0 | 0 | 0 | 0 | 16 |
| TCB | 16 | 1.293 | 0 | 0,00% | 0 | 0 | 0 | 0 | 16 |
| TPB | 16 | 1.080 | 0 | 0,00% | 0 | 0 | 0 | 0 | 16 |
| VAB | 16 | 784 | 0 | 0,00% | 0 | 0 | 0 | 0 | 16 |
| VBB | 17 | 813 | 0 | 0,00% | 0 | 0 | 0 | 0 | 17 |
| **Tổng** | **279** | **15.335** | **6.286** | **40,99%** | **130** | **37** | **32** | **61** | **149** |

## Cách đọc trạng thái

- **PDF hoàn tất:** toàn bộ trang tiếng Việt trong phạm vi PDF đã có JSON hợp
  lệ và manifest toàn PDF đã được xác thực.
- **PDF cần retry:** PDF đã chạy nhưng còn một số trang cần thử lại trong giới
  hạn thông thường; trang đã có JSON hợp lệ được lấy từ cache, không gửi lại.
- **PDF chờ sửa trang lỗi:** PDF đã hết lượt thông thường. Sau khi hàng đợi
  thường kết thúc, terminal-repair mới được phép xử lý tối đa hai lượt, chỉ
  đúng các trang lỗi có receipt.
- **PDF chưa bắt đầu:** chưa gửi bất kỳ trang nào của PDF đó.

Tỷ lệ chính để theo dõi chi phí và khối lượng là **trang JSON hợp lệ / tổng
trang tiếng Việt**. Tỷ lệ PDF hoàn tất thấp hơn vì nhiều PDF chỉ còn thiếu một
hoặc vài trang nhưng chưa được phép coi là hoàn tất.
