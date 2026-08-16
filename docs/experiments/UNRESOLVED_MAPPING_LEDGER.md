# Unresolved mapping and adjudication review ledger

Updated: 2026-08-16 (UTC)

This is the cumulative human-readable file requested for every source item or
family region that could not initially be mapped.  Entries remain here after
resolution so the project owner can audit the original issue, the adjudication,
and the exact result that closed it.  `NO_COMPLETE_REGION` alone never means a
family is absent; report-level absence is recorded only when the project owner
explicitly confirms it for the bound PDF.

This is the single cross-family review file.  Every new unresolved entry records,
when applicable: family, bank, report and reporting period, exact PDF/page/region
locator, raw VietOCR Transformer text, accentless normalized text, independent
pixel transcription when they disagree, visible values and axes, nearest schema
candidate, accounting/structure checks that passed or failed, the unresolved
reason, and the next evidence needed.  Bank/report/page fields are evidence
locators only and are never parser or mapping conditions.

Ledger total: **244 entries**.  Current open queue: **71**.  Closed history:
**99** row/graph resolutions and **74** confirmed bound-report family absences.
Later families append here rather than creating disconnected candidate lists.
Bank/report/page fields below are evidence locators only, never matching rules.

E-0107 `Tiền, kim loại quý và đá quý` trên tám BCTC hợp nhất kiểm toán năm
2025 không bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại ACB p45,
MBB p46, VPB p41, HDB p33, VCB p35, CTG p39, BID p39 và VIB p35. 35 mapping
và tám phương trình tổng đã `VERIFIED_BY_CODEX`. VietOCR đọc số HDB
`1.194.005`, nhưng pixel cùng trục số nguồn xác nhận `1.194.085` và phương
trình đóng đúng; dấu gạch CTG bị provider bỏ sót được bind từ đúng ô ảnh rồi
chuẩn hóa 0. Hai bất đồng là đối chứng OCR đã đóng, không phải khoảng trống
mapping.

E-0108 `Tiền gửi tại NHNN` trên tám BCTC hợp nhất kiểm toán năm 2025 không
bổ sung dòng OPEN: whole-PDF graph tìm đúng một vùng tại cả tám bank và map 28
dòng với mười phương trình đóng chính xác. Tiền gửi tại ngân hàng trung ương
Lào/Campuchia được gom có kiểm soát vào 574 tại MBB/VCB/BID. Graph đã sửa lỗi
subtree tổng quát tại BID: các nhánh VND/ngoại tệ của từng jurisdiction phải
kết thúc trước khi tìm tổng family `123.629.833`. VietOCR HDB `B.416.558` được
pixel và trục số nguồn xác nhận là `8.416.558`; đây là lỗi OCR đã đóng.

E-0079 `Thu nhập lãi và các khoản thu nhập tương tự` không bổ sung dòng OPEN:
cả tám vùng duy nhất đã map hết các dòng nguồn vào 1143–1150. Hai lỗi mất chữ
số đầu của VietOCR tại VIB được trục số nguồn/PaddleOCR và pixel bác bỏ, nên là
đối chứng OCR đã đóng chứ không phải khoảng trống mapping.

E-0080 đóng GN-001–GN-004 và IVP-001–IVP-004/IVP-008 theo quyết định của chủ
dự án. Ba cách gọi khoản vay ngân hàng trung ương dùng schema mới 6070; tiền
gửi có kỳ hạn KBNN dùng 6071; tiền gửi Bộ Tài chính được chuyển từ 1039 sang
6072. ACB đúng 5 năm dùng biên kỳ hạn bao gồm 5 năm, MBB dùng trực tiếp hai
leaf rộng 6010/6009, và trái phiếu tăng vốn BIDV dùng 1117. Tại MBB, 6010
`Dưới 5 năm` và 1112 `Trên 5 năm` là hai hàng trái phiếu tách biệt; 6009 nhận
nguyên dòng chứng chỉ tiền gửi `Trên 12 tháng`. Chỉ ba trục kỳ hạn toàn family
của VPB còn OPEN.

E-0081 `Chi phí lãi và các khoản tương tự chi phí lãi` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một vùng tại cả tám bank và map đủ owner/tổng
1151 cùng bốn dòng con 1152/1153/1154/1156. ReportNormId 1155 được ghi nhận
không xuất hiện trong đúng tám vùng family đã bind. Lỗi VietOCR MBB
`(3:975.549)` được trục số nguồn và pixel bác bỏ thành `(3.975.549)`; đây là
đối chứng OCR đã đóng, không phải khoảng trống mapping.

E-0082 `Thu nhập/chi phí/lãi thuần từ hoạt động dịch vụ` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại MBB/VPB/VIB, map 43 dòng
vào 1157–1174, 5986–5989 và 6021–6025, đồng thời đóng 18 phương trình. Hai
dấu gạch ở `Chi về dịch vụ tư vấn` của MBB được pixel-bind và chuẩn hóa 0.
ACB/HDB/CTG/BID chỉ có tổng trên KQKD; VCB có thêm đối chứng báo cáo bộ phận;
không vùng nào có các hàng con của note nên năm báo cáo được ghi bounded
non-observation, không tạo candidate hoặc dòng OPEN giả.

E-0083 `Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối` không bổ sung
dòng OPEN: whole-PDF graph tìm đúng một note chi tiết tại MBB p47, VPB p63 và
VIB p46, map 23 dòng vào 1175–1185 cùng 6026–6027 và đóng 18 phương trình.
MBB dùng biến thể gộp ngoại tệ giao ngay + vàng với tổng cha ở cuối; VPB tách
vàng riêng; VIB không có dòng vàng; VPB/VIB dùng tổng cha ở đầu. ACB/HDB/VCB/
CTG/BID chỉ có dòng tổng KQKD hoặc đối chứng chính sách/rủi ro/tỷ giá, không có
các hàng con của note; năm báo cáo được ghi bounded non-observation, không tạo
candidate hay dòng OPEN giả. VPB giữ đúng kỳ Q1/2026.

E-0084 `Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/VCB/CTG/
BID, map 28 dòng vào 1188–1191 và đóng 14 phương trình hai kỳ. Dấu `-` kỳ so
sánh của HDB được pixel-bind và chuẩn hóa 0. PDF HDB thực sự in nhãn dự phòng
`chứng khoán đầu tư` bên trong owner chứng khoán kinh doanh; nhãn nguồn được
giữ nguyên, còn containment, vị trí hàng và hai phương trình xác nhận vai trò
1191 nên đây là caveat đã đóng, không phải sửa OCR hay dòng OPEN. VIB chỉ có
note mua bán chứng khoán đầu tư p46; vùng này là đối chứng family khác và không
bị relabel. VPB giữ đúng kỳ Q1/2026.

E-0085 `Lãi/lỗ thuần từ mua bán chứng khoán đầu tư` không bổ sung dòng OPEN:
whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/CTG/BID/VIB,
map 28 dòng vào 1193–1196 và 6028, đồng thời đóng 14 phương trình hai kỳ. MBB
có thêm nhánh dự phòng giảm giá góp vốn, đầu tư dài hạn; VIB không có nhánh dự
phòng. Ba dấu gạch ACB và một dấu gạch MBB được pixel-bind rồi chuẩn hóa 0. VCB
chỉ có số tổng báo cáo bộ phận, không có các hàng con của note nên là bounded
non-observation chứ không tạo candidate hoặc dòng OPEN. VPB giữ đúng kỳ Q1/2026.

E-0086 `Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư` không bổ sung
dòng OPEN: whole-PDF graph chỉ tìm đúng một dòng tổng hợp có hai giá trị tại
MBB p47. Hai phương trình với net chứng khoán kinh doanh và net chứng khoán đầu
tư đóng đúng; bảy PDF còn lại không in dòng tổng hợp tương đương trong phạm vi
nguồn đã bind.

E-0087 `Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức` không bổ sung dòng
OPEN: whole-PDF graph tìm đúng một note chi tiết tại ACB/MBB/VPB/HDB/VCB/CTG/
BID, map 27 dòng vào 1198–1204 và đóng 16 phương trình. Năm dấu gạch được bind
nguồn/pixel và chuẩn hóa 0; hai proposal VietOCR `1` của VPB bị native source
`-` bác bỏ. VIB chỉ có dòng tổng KQKD, không có note chi tiết nên là bounded
non-observation, không tạo candidate. VPB giữ đúng kỳ Q1/2026.

E-0088 `Chi phí quản lý chung (Chi phí hoạt động)` quét đủ 453 trang và tìm
đúng một note tại cả tám PDF. 99 dòng schema/198 ô số cùng 30 phương trình đã
`VERIFIED_BY_CODEX`; một lỗi mất chữ số của VietOCR tại VCB bị pixel và trục số
nguồn bác bỏ. OE-001–OE-004 vẫn OPEN vì là bốn ý nghĩa chi phí riêng chưa có
leaf schema tương đương; chúng vẫn được giữ trong parent/tổng nguồn và không
cản các mapping chắc chắn khác. VPB giữ đúng kỳ Q1/2026.

E-0089 `Chi phí dự phòng rủi ro tín dụng` quét đủ 453 trang và tìm đúng một
note chi tiết tại MBB p49, VPB p66 và VIB p47. 15 mapping/30 ô số và 8 phương
trình đã `VERIFIED_BY_CODEX`; hai dấu gạch không có OCR line được pixel-bind,
hai dấu gạch VPB bị VietOCR đọc thành `1` được native source bác bỏ. E-0100 đã
đóng CRPE-001/CRPE-002 vào 1228 `Dự phòng khác` theo quyết định chủ dự án và
tái kiểm tra tổng nguồn. ACB/HDB/VCB/CTG/BID được ghi nhận bounded absence
cho đúng note chi tiết trong các PDF đã bind, không phải vắng mặt số tổng KQKD.

E-0090 `Thu nhập, chi phí và lãi thuần từ hoạt động khác` quét đủ 453 trang và
tìm đúng một note chi tiết tại MBB p47, VPB p64 và VIB p46. 23 mapping/46 ô số
và 14 phương trình đã `VERIFIED_BY_CODEX`; MBB dùng biến thể net-only,
VPB/VIB dùng parent thu nhập + parent chi phí + các nhánh tùy chọn + lãi thuần.
Hai dòng thanh lý tài sản của VPB được cộng có kiểm soát theo từng kỳ. E-0100
đã cộng OACT-001 vào 1239 `Khác` đúng một lần và tái đóng parent thu nhập.
ACB/HDB/VCB/CTG/BID là bounded detailed-note absence; tổng KQKD, segment và
diễn giải không bị relabel thành note chi tiết. VPB giữ đúng kỳ Q1/2026.

E-0091 `Chi phí thuế thu nhập doanh nghiệp` quét đủ 453 trang và tìm đúng một
bảng đối chiếu chi tiết tại MBB p50, VPB p59 và VIB p48. 28 mapping/56 ô số và
20 phương trình đã `VERIFIED_BY_CODEX`; toàn bộ schema 5723–5737 được quan sát
và xác minh qua các biến thể. Hai dấu `-` của VPB chỉ được chuẩn hóa thành 0 sau
khi trục số nguồn xác nhận. TAX-001 còn OPEN vì VIB chỉ ghi `Điều chỉnh khác`,
kỳ hiện tại để trống và kỳ so sánh là `163`; nhãn này không đủ để ép vào leaf
5733 về điều chỉnh thuế của các năm trước. ACB/HDB/VCB/CTG/BID là bounded
detailed-note absence; tổng KQKD/nghĩa vụ thuế/thuế hoãn lại không bị relabel.

E-0092 `Tiền và các khoản tương đương tiền` quét đủ 453 trang và tìm đúng một
vùng chi tiết tại ACB p8, MBB p50, VPB p66, VCB p40, CTG p47 và VIB p45. 31
mapping/60 ô số và 12 phương trình đã `VERIFIED_BY_CODEX`, phủ toàn bộ family
1248–1254. Hai ô chứng khoán không in số được giữ trống thay vì đổi thành 0.
Không còn dòng nguồn chưa map trong sáu vùng. HDB/BID là bounded detailed-note
absence; số dư đầu/cuối kỳ và chính sách gần giống không bị relabel.

E-0093 `Mua mới và thanh lý các công ty con` quét đủ 453 trang và không tìm
thấy bảng nào có đủ ba dòng 1256–1258. Cả tám PDF là bounded detailed-note
absence, không phải khẳng định không có lịch sử giao dịch. HDB có HDS trở thành
công ty con nhưng đang áp dụng phương pháp tạm thời; CTG có caption dòng tiền
mua/bán công ty con. Các đối chứng này thiếu tổng giá trị, tiền thanh toán và
tiền thực có trong công ty con nên không phát sinh mapping hay dòng OPEN.

E-0094 `Thu nhập nhân viên của ngân hàng` quét đủ 453 trang và tìm đúng một
vùng chi tiết tại ACB p26, VPB p66 và VIB p49. 13 mapping/26 ô số và 14
phương trình tổng hoặc tỷ lệ đã `VERIFIED_BY_CODEX`. VPB giữ đúng kỳ Q1/2026;
VIB dùng kỳ sáu tháng. E-0100 chia hai số bình quân ACB cho đúng sáu tháng,
lưu phân số chính xác và map vào 1267/1268. MBB/HDB/VCB/CTG/BID không có bảng thu nhập nhân
viên chi tiết trong các PDF đã bind.

E-0095 `Tình hình thực hiện nghĩa vụ với ngân sách nhà nước` quét đủ 453
trang và tìm đúng một vùng tại ACB p22, MBB p49, VPB p58, HDB p32, CTG p43,
BID p26 và VIB p47. 33 mapping/147 ô số và 37 phương trình đã
`VERIFIED_BY_CODEX`. HDB dùng thêm trục tăng do hợp nhất; CTG tách phải nộp,
phải thu và số thuần cuối kỳ. 13 dấu gạch chỉ được chuẩn hóa thành 0 sau khi
xem pixel. E-0100 đưa `Tiền thuê đất` vào 1279 `Các khoản phải nộp khác`; năm
dấu gạch nhìn thấy đều bằng 0 nên mapping gộp không làm đổi tổng. VCB là bounded detailed-note absence; VPB giữ đúng
kỳ Q1/2026.

E-0096 `Tài sản thế chấp của khách hàng mà ngân hàng đang nắm giữ` quét đủ
453 trang và tìm đúng một vùng tại VPB p67, VCB p47 và VIB p49. 15 mapping/30
ô số và sáu phương trình tổng đã `VERIFIED_BY_CODEX`. VIB dùng parent `Của
khách hàng` trong note chung nên nhánh `Của các TCTD khác` và tài sản chính
ngân hàng đưa đi thế chấp không bị nhập nhầm. E-0100 đã gộp CC-001–CC-004 vào
1288 `Khác` đúng một lần theo bank; hai tổng VCB/VIB tiếp tục đóng chính xác. ACB/MBB/HDB/CTG/
BID là bounded detailed-note absence; VPB giữ đúng kỳ Q1/2026.

E-0097 `Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu`
quét đủ 453 trang và tìm đúng một vùng tại VPB p67 và VIB p49. Năm mapping/10
ô số và sáu quan hệ thành phần đã `VERIFIED_BY_CODEX`; ACB/MBB/HDB/VCB/CTG/
BID là bounded detailed-note absence. BPA-001 giữ nguyên parent gộp của VPB vì
tổng nguồn in cộng cả parent lẫn các con “Trong đó”, nên hai phép tái hiện tổng
chỉ là source-presentation reconciliation chứ không phải accounting identity.
BPA-002/BPA-003 giữ hai hàng GTCG chung của VIB thay vì ép vào chứng khoán kinh
doanh/đầu tư khi PDF không in phân rã. VPB giữ đúng kỳ Q1/2026.

E-0098 `Nghĩa vụ nợ tiềm ẩn và các cam kết đưa ra` quét đủ 453 trang và tìm
đúng một note chi tiết tại ACB p26, MBB p51, VPB p68, CTG p48 và VIB p50.
47 mapping/92 ô số và 34 phương trình đã `VERIFIED_BY_CODEX`. VIB map cột
giá trị thuần sau ký quỹ; cột gộp và ký quỹ được giữ làm accounting controls.
CL-001–CL-005 và CL-007–CL-014 còn OPEN vì là các leaf L/C, ký quỹ, bảo lãnh
chi tiết, swap lãi suất hoặc `Trong đó` chưa có schema tương đương. HDB/VCB/BID
chỉ có bảng B02a và là bounded detailed-note absence; VPB giữ đúng kỳ Q1/2026.

E-0099 `Công cụ tài chính — giá trị ghi sổ và giá trị hợp lý` quét đủ 453
trang và tìm đúng một bảng tại VPB p86, VCB p44–45 và CTG p51. 64 mapping/55
ô số và 12 phương trình đã `VERIFIED_BY_CODEX`; một dấu gạch CTG được
pixel-bind rồi chuẩn hóa 0. ACB/MBB/HDB/BID/VIB là bounded detailed-table
absence; các bảng rủi ro tiền tệ/lãi suất/thanh khoản là đối chứng âm. FI-001–
FI-003 giữ OPEN vì nguồn in `(*)` và ghi rõ giá trị hợp lý không xác định được;
không đổi `(*)` thành 0 hay sao chép giá trị ghi sổ. VPB giữ đúng kỳ Q1/2026.

E-0101 `Rủi ro tiền tệ` là base whole-PDF scan: sáu vùng duy nhất tại MBB p58,
VPB p80, HDB p38–39, VCB p50–51, CTG p60, VIB p65–66; ACB/BID là bounded
absence. E-0105 đóng CRISK-001/003–006/008/010–011 bằng quyết định làm tròn
±1, dấu gạch ngoại bảng bằng 0 và phạm vi bảng VCB→1418. Chỉ CRISK-002/007/009
còn OPEN vì schema chưa có trục vàng; không gộp vàng vào `Tiền tệ khác`.

E-0102 `Rủi ro lãi suất` là base whole-PDF scan: sáu vùng duy nhất tại MBB p57,
VPB p78, HDB p40–41, VCB p48–49, CTG p55, VIB p62–63; ACB/BID là bounded
absence. E-0105 đóng toàn bộ IRISK-001–IRISK-026. Dấu gạch được pixel-bind
thành 0; HDB được sửa vai trò dòng theo tọa độ đầy đủ; Gemma 4 đọc độc lập
bảng xoay VIB và 36 phương trình bác các chữ số rơi của challenger cũ. Family
hiện không còn dòng OPEN; VietOCR/Gemma vẫn không được dùng đơn lẻ làm numeric
truth. VPB giữ đúng kỳ Q1/2026.

E-0103 `Rủi ro thanh khoản` là base whole-PDF scan: sáu vùng duy nhất tại MBB
p60, VPB p82, HDB p43, VCB p53, CTG p58, VIB p68–69; ACB/BID là bounded
absence. E-0105 đóng LRISK-001/006–019: dấu gạch tổng nợ quá hạn bằng 0 và
Gemma 4 + full-table pixels đọc đủ VIB, khép 16 phương trình. Chỉ LRISK-002–005
còn OPEN vì bốn residual VPB lần lượt 6.000/275.500/6.001/275.499 là trọng yếu,
không được coi là làm tròn. VPB giữ đúng kỳ Q1/2026.

E-0104 `Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo` quét đủ 453 trang
và tìm đúng một vùng tại MBB p61, VPB p90, CTG p61, BID p35 và VIB p71;
ACB/HDB/VCB là bounded detailed-table absence. Graph chung dùng owner tỷ giá,
hai trục kỳ, đơn vị VND/đồng hoặc policy quy đổi VND cấp tài liệu và tối thiểu
hai hàng mã tiền tệ thẳng hàng; không dùng bank/page làm rule. Pixel, trục số
Paddle/native và live schema xác minh 46 mapping/92 ô, đồng thời giữ đủ 122 ô
nguồn. FXRATE-001–FXRATE-015 là 15 dòng tiền/vàng ngoài schema 5935–5945;
chúng đã được xác minh nguồn nhưng vẫn `OPEN`, không bị bỏ hoặc ép vào leaf
khác. VPB giữ đúng kỳ Q1/2026; BID dùng policy VND nhìn thấy tại p13.

## Open review queue (always first)

| ID | Family | Bank | Trang | Khoản mục nguồn | Lý do còn mở |
| --- | --- | --- | ---: | --- | --- |
| FXRATE-001 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | CNY | Không có leaf CNY dưới schema 5935–5945. |
| FXRATE-002 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-003 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | NZD | Không có leaf NZD dưới schema 5935–5945. |
| FXRATE-004 | Tỷ giá ngoại tệ cuối kỳ | VPB | 90 | Vàng (XAU) | Không có leaf vàng/XAU dưới schema 5935–5945. |
| FXRATE-005 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | NZD | Không có leaf NZD dưới schema 5935–5945. |
| FXRATE-006 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | NOK | Không có leaf NOK dưới schema 5935–5945. |
| FXRATE-007 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-008 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | HKD | Không có leaf HKD dưới schema 5935–5945. |
| FXRATE-009 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | CNY | Không có leaf CNY dưới schema 5935–5945. |
| FXRATE-010 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | KRW | Không có leaf KRW dưới schema 5935–5945. |
| FXRATE-011 | Tỷ giá ngoại tệ cuối kỳ | CTG | 61 | LAK | Không có leaf LAK dưới schema 5935–5945. |
| FXRATE-012 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | DKK | Không có leaf DKK dưới schema 5935–5945. |
| FXRATE-013 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | HKD | Không có leaf HKD dưới schema 5935–5945. |
| FXRATE-014 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | NOK | Không có leaf NOK dưới schema 5935–5945. |
| FXRATE-015 | Tỷ giá ngoại tệ cuối kỳ | VIB | 71 | XAU | Không có leaf vàng/XAU dưới schema 5935–5945. |
| LRISK-001 | Rủi ro thanh khoản | MBB | 60 | Quá hạn — tổng tài sản/tổng nợ/chênh lệch ròng | `CLOSED_E0105`: tổng nợ in dấu `-` được chuẩn hóa 0; `28.949.005 - 0 = 28.949.005`. |
| LRISK-002 | Rủi ro thanh khoản | VPB | 82 | 1–3 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `+6.000` so với chênh lệch in. |
| LRISK-003 | Rủi ro thanh khoản | VPB | 82 | 1–5 năm — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `-275.500` so với chênh lệch in. |
| LRISK-004 | Rủi ro thanh khoản | VPB | 82 | 3–12 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `-6.001` so với chênh lệch in. |
| LRISK-005 | Rủi ro thanh khoản | VPB | 82 | Đến 1 tháng — tổng tài sản/tổng nợ/chênh lệch ròng (3 ô) | Phép trừ lệch `+275.499` so với chênh lệch in. |
| LRISK-006–LRISK-007 | Rủi ro thanh khoản | HDB | 43 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-008–LRISK-009 | Rủi ro thanh khoản | VCB | 53 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-010–LRISK-011 | Rủi ro thanh khoản | CTG | 58 | Hai trục quá hạn, 6 ô | `CLOSED_E0105`: hai tổng nợ là dấu `-` = 0; hai phương trình khép đúng. |
| LRISK-012–LRISK-019 | Rủi ro thanh khoản | VIB | 68–69 | Tám trục, 48 ô kỳ hiện tại/so sánh | `CLOSED_E0105`: full-table pixels + Gemma 4 challenger khớp; 16 phương trình tài sản − nợ = chênh lệch khép đúng. |
| IRISK-001–IRISK-002 | Rủi ro lãi suất | MBB/VPB | 57/78 | Quá hạn MBB và tổng trạng thái VPB | `CLOSED_E0105`: dấu `-` = 0; hai phương trình khép đúng. |
| IRISK-003–IRISK-011 | Rủi ro lãi suất | HDB | 41 | Chín trục nội/ngoại/kết hợp | `CLOSED_E0105`: sửa vai trò dòng theo full-render geometry; 18 phương trình khép đúng. |
| IRISK-012–IRISK-015 | Rủi ro lãi suất | VCB | 49 | Bốn trạng thái kết hợp | `CLOSED_E0105`: ngoại bảng in dấu `-` = 0; kết hợp bằng nội bảng. |
| IRISK-016–IRISK-017 | Rủi ro lãi suất | CTG | 55 | Hai trục quá hạn | `CLOSED_E0105`: tổng nợ in dấu `-` = 0; hai phương trình khép đúng. |
| IRISK-018–IRISK-026 | Rủi ro lãi suất | VIB | 62–63 | Chín trục × năm vai trò × hai kỳ = 90 ô | `CLOSED_E0105`: 69 crop cũ + 10 crop bổ sung + 11 dash pixel được Gemma 4/pixel đọc lại; 36 phương trình khép đúng. |
| CRISK-001 | Rủi ro tiền tệ | VPB | 80 | EUR — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | `CLOSED_E0105`: giữ nguyên bốn số nguồn; residual đúng 1 được adjudicate là sai số trình bày/làm tròn, không sửa số. |
| CRISK-002 | Rủi ro tiền tệ | VPB | 80 | Vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Family 1352 chưa có nhánh currency-axis vàng; bốn ô vẫn khép nội bảng. |
| CRISK-003–CRISK-005 | Rủi ro tiền tệ | VPB | 80 | OTHER/TOTAL/USD | `CLOSED_E0105`: map trực tiếp trạng thái kết hợp nhìn thấy; residual TOTAL đúng 1 được giữ là sai số trình bày. |
| CRISK-006 | Rủi ro tiền tệ | HDB | 39 | Trạng thái nội, ngoại bảng — EUR | `CLOSED_E0105`: ngoại bảng in `-` = 0; `3.919 + 0 = 3.919`. |
| CRISK-007 | Rủi ro tiền tệ | HDB | 39 | Vàng — tổng tài sản, tổng nợ, trạng thái nội bảng/kết hợp | Schema chưa có nhánh currency-axis vàng. |
| CRISK-008 | Rủi ro tiền tệ | VCB | 51 | Tổng nợ phải trả — VND | `CLOSED_E0105`: tiêu đề/phạm vi bảng cho phép map giá trị vào 1418 theo quyết định chủ dự án. |
| CRISK-009 | Rủi ro tiền tệ | CTG | 60 | Vàng — tổng tài sản, trạng thái nội bảng/kết hợp | Nguồn để trống tổng nợ và ngoại bảng vàng; schema cũng chưa có nhánh vàng. |
| CRISK-010–CRISK-011 | Rủi ro tiền tệ | VIB | 65 | Trạng thái kết hợp EUR/USD kỳ hiện tại | `CLOSED_E0105`: ngoại bảng in `-` = 0; kết hợp bằng nội bảng trên cả hai trục. |
| FI-001 | Công cụ tài chính | VPB | 86 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Nguồn ghi không thể xác định giá trị hợp lý; ký hiệu không phải 0 và giá trị ghi sổ không thay thế được. |
| FI-002 | Công cụ tài chính | VCB | 45 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Không có giá trị số được công bố; giữ nguyên nhóm nguồn OPEN. |
| FI-003 | Công cụ tài chính | CTG | 51 | Giá trị hợp lý của các tài sản và nợ tài chính đánh dấu `(*)` | Không có giá trị số được công bố; giữ nguyên nhóm nguồn OPEN. |
| CL-001 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Thư tín dụng trả ngay | Parent 1295 chưa có leaf L/C trả ngay; số vẫn đóng đúng L/C thuần. |
| CL-002 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Thư tín dụng trả chậm | Parent 1295 chưa có leaf L/C trả chậm; số vẫn đóng đúng L/C thuần. |
| CL-003 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Trừ: tiền ký quỹ (L/C) | Đây là trục khấu trừ để ra L/C thuần, không phải leaf giá trị hiện có. |
| CL-004 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Bảo lãnh khác (dòng con) | Dòng con lặp lại tên parent `Bảo lãnh khác`; chưa có leaf riêng để không map hai lần vào 1300. |
| CL-005 | Nghĩa vụ nợ tiềm ẩn/cam kết | ACB | 26 | Trừ: tiền ký quỹ (bảo lãnh) | Trục khấu trừ đóng đúng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-007 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trừ: tiền ký quỹ (L/C) | Trục khấu trừ đóng đúng L/C thuần nhưng chưa có leaf schema. |
| CL-008 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết bảo lãnh khác | Dòng con nằm trong parent `Bảo lãnh khác`; chưa có leaf riêng để tránh double mapping. |
| CL-009 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trừ: tiền ký quỹ (bảo lãnh) | Trục khấu trừ đóng đúng parent bảo lãnh nhưng chưa có leaf schema. |
| CL-010 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất tiền tệ chéo — nhận | Schema hoán đổi tiền tệ 1302/5743–5744 chưa có leaf swap lãi suất chéo nhận. |
| CL-011 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất tiền tệ chéo — trả | Schema chưa có leaf swap lãi suất chéo trả. |
| CL-012 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết hoán đổi lãi suất một đồng tiền | Schema chưa có leaf swap lãi suất một đồng tiền. |
| CL-013 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Cam kết khác (dòng con) | Dòng con lặp tên parent 1304; giữ trong phương trình parent, không map hai lần. |
| CL-014 | Nghĩa vụ nợ tiềm ẩn/cam kết | VPB | 68 | Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang | Dòng `Trong đó` là non-additive và chưa có leaf riêng. |
| BPA-001 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VPB | 67 | Giấy tờ có giá đưa đi thế chấp, cầm cố | Parent gộp bằng hai con “Trong đó”, nhưng tổng nguồn lại cộng parent và hai con lần nữa; giữ source-only, không biến hierarchy double-count thành accounting identity. |
| BPA-002 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VIB | 49 | Giấy tờ có giá đưa đi thế chấp, cầm cố | Nguồn không tách chứng khoán kinh doanh/đầu tư nên không ép vào 1290/1291. |
| BPA-003 | Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu | VIB | 49 | Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu | Nguồn không tách loại chứng khoán; family 1289–1293 chưa có leaf mục đích sử dụng tương đương. |
| TAX-001 | Chi phí thuế thu nhập doanh nghiệp | VIB | 48 | Điều chỉnh khác | Nhãn rộng hơn leaf 5733; kỳ hiện tại để trống và không được coi là 0, kỳ so sánh `163` vẫn tham gia phương trình tổng thuế hiện hành đã xác minh. |
| OE-001 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi thuê tài sản | Chưa có leaf riêng dưới 1212 `Chi về tài sản`; dòng vẫn nằm trong parent nguồn đã xác minh. |
| OE-002 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi phí công nghệ thông tin | Chưa có leaf chi phí CNTT tương đương trong family 1205–1220. |
| OE-003 | Chi phí quản lý chung (Chi phí hoạt động) | VPB | 65 | Chi về thuế GTGT đầu vào không được khấu trừ | Chưa có leaf chi phí VAT đầu vào không khấu trừ tương đương. |
| OE-004 | Chi phí quản lý chung (Chi phí hoạt động) | CTG | 47 | Chi khác về TSCĐ | Chưa có leaf riêng dưới 1212; hai số nguồn vẫn đóng đúng phương trình `khấu hao + chi khác về TSCĐ = chi về tài sản`. |
| CAF-001 | Vốn và các quỹ | VPB | 60 | Quỹ đầu tư phát triển | Chưa có cột số dư vốn tương đương trong schema; giá trị vẫn nằm trong tổng vốn đã xác minh. |
| CAF-002 | Vốn và các quỹ | VPB | 60 | Cổ phiếu quỹ | Không đồng nhất với nhánh số lượng cổ phiếu 5953; dấu gạch không được tự dùng làm numeric authority. |
| CAF-003 | Vốn và các quỹ | HDB | 33 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; cột trống không bị đổi thành 0. |
| CAF-004 | Vốn và các quỹ | HDB | 33 | Quỹ đầu tư xây dựng cơ bản | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| CAF-005 | Vốn và các quỹ | VCB | 36 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong subtotal quỹ và tổng vốn đã xác minh. |
| CAF-006 | Vốn và các quỹ | CTG | 43 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; dòng trống không bị đổi thành 0. |
| CAF-007 | Vốn và các quỹ | CTG | 43 | Chênh lệch đánh giá lại tài sản | Chưa có cột số dư vốn tương đương trong schema. |
| CAF-008 | Vốn và các quỹ | CTG | 43 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã xác minh. |
| CAF-009 | Vốn và các quỹ | BID | 27–28 | Báo cáo tình hình thay đổi vốn chủ sở hữu | Cấu trúc bảng xoay đã unique; OCR số nguồn không đủ tin cậy nên chưa map, và VietOCR text không được dùng làm numeric truth. |
| CAF-010 | Vốn và các quỹ | VIB | 44–45 | Báo cáo tình hình thay đổi vốn chủ sở hữu | Cấu trúc bảng xoay đã unique; OCR số nguồn không đủ tin cậy nên chưa map, và VietOCR text không được dùng làm numeric truth. |
| OPL-001 | Các khoản phải trả và công nợ khác | ACB | 22 | Thu nhập chưa thực hiện | Chưa có leaf tương đương trong family 1118–1127; giá trị vẫn nằm trong tổng family đã xác minh. |
| OPL-002 | Các khoản phải trả và công nợ khác | ACB | 22 | Quỹ phát triển khoa học và công nghệ | Chưa có leaf tương đương; giá trị vẫn nằm trong tổng family đã xác minh. |
| OPL-003 | Các khoản phải trả và công nợ khác | VPB | 57 | Các khoản khách hàng trả trước | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-004 | Các khoản phải trả và công nợ khác | VPB | 57 | Doanh thu chờ phân bổ | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-005 | Các khoản phải trả và công nợ khác | VPB | 57 | Dự phòng nghiệp vụ bảo hiểm | Không đồng nhất với 1125 `Dự phòng rủi ro khác`. |
| OPL-006 | Các khoản phải trả và công nợ khác | VPB | 57 | Các khoản treo chờ chuyển tiền | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-007 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả hoạt động thanh toán thẻ | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-008 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả nhà cung cấp | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-009 | Các khoản phải trả và công nợ khác | VPB | 57 | Phải trả các khoản vay khách hàng của VPBankS | Chưa có leaf tương đương cho nghĩa vụ của công ty con. |
| OPL-010 | Các khoản phải trả và công nợ khác | VPB | 57 | Tiền giữ hộ và đợi thanh toán | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-011 | Các khoản phải trả và công nợ khác | CTG | 43 | Các khoản lãi, phí phải trả | Chưa có leaf tương đương; giá trị vẫn nằm trong tổng family đã xác minh. |
| OPL-012 | Các khoản phải trả và công nợ khác | VIB | 43 | Các khoản lãi, phí phải trả | Chưa có leaf tương đương; giá trị vẫn nằm trong tổng family đã xác minh. |
| OPL-013 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả cổ tức cho cổ đông | Chưa có leaf tương đương; chỉ nằm trong parent phải trả nội bộ. |
| OPL-014 | Các khoản phải trả và công nợ khác | VIB | 43 | Tiền giữ hộ và đợi thanh toán | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-015 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả thanh toán giữa các TCTD | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-016 | Các khoản phải trả và công nợ khác | VIB | 43 | Phải trả chuyển tiền chờ thanh toán | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-017 | Các khoản phải trả và công nợ khác | VIB | 43 | Các khoản chờ thanh toán khác | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| OPL-018 | Các khoản phải trả và công nợ khác | VIB | 43 | Doanh thu chờ phân bổ | Chưa có leaf tương đương; giá trị vẫn nằm trong tổng family đã xác minh. |
| PM-001 | Dự phòng rủi ro cho vay khách hàng | VPB | 45 | Dự phòng chung, dự phòng cụ thể, dự phòng cho vay giao dịch ký quỹ và ứng trước | Đã map và kiểm tra đủ kỳ 01/01–31/03/2026 của PDF được cung cấp; chưa có PDF VPB Q2/2026 nên không được relabel kết quả Q1 thành Q2. |
| OA-001 | Tài sản Có khác | VPB | 51 | Phải thu bán tài sản tài chính | Nghĩa nguồn rộng hơn 976 `Phải thu từ bán chứng khoán`; không thu hẹp ngầm. |
| OA-002 | Tài sản Có khác | VPB | 51 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có khoản mục con tương đương trong family 966–1023. |
| OA-003 | Tài sản Có khác | VPB | 52 | Số dư đầu kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-004 | Tài sản Có khác | VPB | 52 | Trích lập dự phòng rủi ro trong kỳ | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-005 | Tài sản Có khác | VPB | 52 | Số dư cuối kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| OA-006 | Tài sản Có khác | VPB | 52 | Dự phòng tài sản Có rủi ro tín dụng | Đây là phân rã số dư dự phòng, không phải population chất lượng 1018. |
| OA-007 | Tài sản Có khác | VPB | 52 | Dự phòng cụ thể | Chưa có khoản mục dự phòng `Tài sản Có khác`. |
| OA-008 | Tài sản Có khác | VPB | 52 | Dự phòng rủi ro phải thu khó đòi | Chưa có khoản mục con tương đương. |
| OA-009 | Tài sản Có khác | VIB | 39 | Phải thu từ Ngân sách Nhà nước | Không đồng nhất với 979 `Phải thu từ NHNN Việt Nam`. |
| OA-010 | Tài sản Có khác | VIB | 39 | Phải thu từ hoạt động tài trợ thương mại | Chưa có khoản mục con tương đương. |
| OA-011 | Tài sản Có khác | VIB | 39 | Phải thu hoa hồng bảo hiểm | Chưa chứng minh tương đương khoản phải thu từ công ty bảo hiểm con. |
| OA-012 | Tài sản Có khác | VIB | 39 | Tài sản thuế TNDN hoãn lại | Chưa có khoản mục con tương đương trong family 966–1023. |
| IVP-005 | Phát hành giấy tờ có giá | VPB | 56 | Dưới 12 tháng | Trục kỳ hạn áp dụng cho toàn family gồm chứng chỉ tiền gửi và trái phiếu, không riêng một instrument leaf. |
| IVP-006 | Phát hành giấy tờ có giá | VPB | 56 | Từ trên 12 tháng đến 5 năm | Trục kỳ hạn toàn family, không được gán riêng vào CD/kỳ phiếu/trái phiếu. |
| IVP-007 | Phát hành giấy tờ có giá | VPB | 56 | Từ trên 5 năm trở lên | Trục kỳ hạn toàn family, không được gán riêng vào CD/kỳ phiếu/trái phiếu. |

The shared family locator follows a strict minimal-anchor search.  It enumerates
every parent+child pair first, then every child+child pair, over both complete and
near branch regions in the entire PDF.  If one pair is unique it stops; if pairs
collide it tries every remaining pair before expanding to parent+two-child or
three-child combinations.  Large monetary rows only prioritize which pair is
tested first.  They do not grant mapping authority.  The selected pair locates a
region but never truncates it: the retained graph still contains every observed
row, axis, optional branch, total and accounting relation.  Sibling order is not
fixed, while the parent must precede its descendant region.  No bank, filename,
page or note identifier participates in this decision.

| IDs | Current disposition |
| --- | --- |
| LG-001–LG-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; MBB/VIB alone have the exact customer-loan geography family. Five broader total-loan tables and VCB's segment report stay negative controls, never narrowed or relabelled |
| IDL-001–IDL-002 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận HDB/VCB bắt đầu thuyết minh từ family 592 |
| CBD-001–CBD-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; hai dòng cộng thành 2.148.359 và map vào ReportNormId 574 `Tiền gửi khác` |
| LT-001–LT-002 | `RESOLVED_VERIFIED_BY_CODEX` |
| LI-001, LI-008, LI-009 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT` |
| LI-002–LI-007, LI-010–LI-011 | `RESOLVED_VERIFIED_BY_CODEX` |
| LE-001–LE-011 | `RESOLVED` by exact family replay, non-additive graph equivalence, or pixel replay |
| CD-001–CD-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VPB `64.165` và VIB `174` map vào schema 770 đã đổi tên để bao quát MTV hoặc trên MTV có vốn Nhà nước trên 50% |
| PM-001 | `OPEN_SOURCE_PERIOD_GAP`; không còn dòng nguồn chưa map trong PDF Q1 đã bind |
| SEC-001 | `RESOLVED_VERIFIED_BY_CODEX`; E-0067 đã xử lý AFS VIB, map trực tiếp 807/824 và chuyển riêng phép gộp TCTD sang IS-002 |
| CPM-001–CPM-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận các mốc bắt đầu thuyết minh loại trừ family 561 trong năm PDF |
| IS-001 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; BID p23 kế thừa tuyên bố `Triệu VND` nhìn thấy tại p13 của cùng PDF và toàn vùng AFS/HTM được replay-bound |
| IS-002 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; VIB gộp đúng hai dòng TCTD theo từng kỳ vào ReportNormId 808, giữ nguyên hai thành phần và hai phương trình |
| DFI-001 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; chủ dự án xác nhận VCB không có thuyết minh family 631 |
| IFA-001–IFA-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng biến động TSCĐ vô hình chi tiết trong PDF đã bind |
| IFA-006 | `RESOLVED_VERIFIED_BY_CODEX`; schema 6069 được thêm và map cho disclosure TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng tại VPB/VIB |
| IP-001–IP-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/VPB/HDB/VCB/CTG/BID/VIB không có bảng biến động bất động sản đầu tư chi tiết trong đúng PDF đã bind; statement, policy, cash-flow và expense mentions giữ làm đối chứng âm |
| OA-001–OA-012 | `OPEN_SCHEMA_OR_SEMANTIC_GAP`; 58 khoản mục chắc chắn vẫn đã map, 12 dòng này được giữ nguyên nguồn và không ép vào schema gần nhất |
| GN-001–GN-004 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; ba nhãn vay NHNN/Ngân hàng Trung ương map 6070, tiền gửi có kỳ hạn KBNN map 6071; BID `Tiền gửi Bộ Tài chính` được chuyển khỏi 1039 sang 6072 |
| EIR-001–EIR-005 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID chuyển từ tiền gửi khách hàng thẳng sang family nợ kế tiếp, không có note vốn nhận tài trợ/ủy thác trong PDF đã bind |
| EIR-006–EIR-007 | `RESOLVED_VERIFIED_BY_CODEX`; hai nguồn nhỏ chưa có leaf riêng — ODA của VPB và chương trình nhà ở qua NHNN của VIB — giữ nguyên nhãn nguồn và map vào leaf `Khác` 1099 |
| IVP-001–IVP-004, IVP-008 | `RESOLVED_VERIFIED_BY_PROJECT_OWNER_AND_CODEX`; ACB đúng 5 năm map 1103/1111, MBB broad tenor map trực tiếp 6009/6010, BID trái phiếu tăng vốn map 1117 |
| IVP-005–IVP-007 | `OPEN_SOURCE_SCOPE_GAP`; ba kỳ hạn VPB áp dụng cho toàn family, chưa có phân bổ nhìn thấy theo từng công cụ |
| OPL-001–OPL-018 | `OPEN_SCHEMA_OR_SEMANTIC_GAP`; 39 khoản mục chắc chắn vẫn đã map. Các dòng chưa có leaf vẫn được giữ trong parent/tổng nguồn và không bị cộng hai lần |
| OE-001–OE-004 | `OPEN_SCHEMA_GAP`; 99 khoản mục chắc chắn vẫn đã map. Bốn dòng chi phí riêng được giữ trong parent/tổng và các phương trình nguồn, không ép vào leaf gần nghĩa |
| CRPE-001–CRPE-002 | `CLOSED_BY_PROJECT_OWNER_TO_1228`; E-0100 giữ nguyên bốn giá trị nguồn, map hai dòng vào `Dự phòng khác` và tái đóng đúng tổng VPB/VIB |
| CRPE-003–CRPE-007 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có note chi tiết 1221 trong PDF đã bind, dù có thể có dòng tổng KQKD hoặc diễn giải chính sách |
| OACT-001 | `CLOSED_BY_PROJECT_OWNER_TO_1239`; E-0100 cộng `41 / 9` vào dòng Khác hiện có đúng một lần và tái đóng parent thu nhập VPB |
| OACT-002–OACT-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có note hoạt động khác chi tiết trong PDF đã bind; tổng KQKD, segment và diễn giải là đối chứng âm |
| TAX-001 | `OPEN_SCHEMA_GAP_WITH_BLANK_CURRENT_AXIS`; 28 khoản mục chắc chắn vẫn đã map. Dòng VIB `Điều chỉnh khác` chỉ có số kỳ so sánh `163`; ô kỳ hiện tại trống không bị đổi thành 0 và nhãn không bị ép vào 5733 |
| TAX-002–TAX-006 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/HDB/VCB/CTG/BID không có bảng đối chiếu chi phí thuế chi tiết trong PDF đã bind |
| CEQ-001–CEQ-002 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; HDB/BID không có bảng chi tiết tiền và tương đương tiền 1248–1254 trong PDF đã bind; số dư lưu chuyển tiền tệ và diễn giải chính sách là đối chứng âm |
| SAD-001–SAD-008 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; cả tám PDF không có bảng chi tiết 1255–1258. Giao dịch HDS của HDB và caption dòng tiền CTG được giữ làm đối chứng, không bị relabel |
| EI-001–EI-002 | `CLOSED_BY_PROJECT_OWNER_MONTHLY_DERIVATION`; E-0100 chia chính xác các số sáu tháng cho 6: lương `15 / 43÷3`, thu nhập `81÷2 / 247÷6`, rồi map 1267/1268 |
| SBO-001 | `CLOSED_BY_PROJECT_OWNER_TO_1279`; năm dấu gạch HDB được pixel-bind thành 0 và gộp vào `Các khoản phải nộp khác`, không làm đổi tổng |
| CC-001–CC-004 | `CLOSED_BY_PROJECT_OWNER_TO_1288`; E-0100 gộp một lần vào dòng Khác hiện có. VCB 1288 thành `688.039.608 / 687.893.688`; VIB thành `204.865.534 / 153.501.606`, và hai total đóng đúng |
| BPA-001–BPA-003 | `OPEN_SOURCE_HIERARCHY_OR_SCHEMA_GAP`; VPB parent gộp bị tổng nguồn cộng lặp với các con, còn hai hàng VIB không tách loại chứng khoán; không dòng nào bị ép vào hierarchy/leaf hẹp |
| CL-001–CL-005, CL-007–CL-014 | `OPEN_SCHEMA_OR_SOURCE_HIERARCHY_GAP`; 47 mapping chắc chắn và 34 phương trình vẫn đã xác minh; các leaf/trục khấu trừ/`Trong đó` chưa tương đương được giữ nguyên nguồn |
| CL-023–CL-025 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; HDB/VCB/BID có bảng B02a ngoài báo cáo chính nhưng không có note B05a chi tiết của family trong đúng PDF đã bind |
| FI-001–FI-003 | `OPEN_SOURCE_VALUE_UNAVAILABLE`; VPB/VCB/CTG in `(*)` thay cho phần lớn giá trị hợp lý. Ký hiệu này không được đổi thành 0 hoặc thay bằng giá trị ghi sổ |
| FI-007–FI-011 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/MBB/HDB/BID/VIB không có bảng chi tiết đồng thời trình bày giá trị ghi sổ và giá trị hợp lý trong đúng PDF đã bind |
| CRISK-001/003–006/008/010–011 | `CLOSED_BY_E0105_PROJECT_OWNER_ADJUDICATION`; dấu gạch ngoại bảng = 0, VCB VND→1418, hai residual đúng 1 giữ nguyên nguồn như sai số trình bày |
| CRISK-002/007/009 | `OPEN_NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH`; 11 ô vàng không bị gộp vào tiền tệ khác |
| CRISK-012–CRISK-013 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro tiền tệ chi tiết trong đúng PDF đã bind |
| IRISK-001–IRISK-026 | `CLOSED_BY_E0105_PIXEL_GEMMA4_AND_ACCOUNTING_REPLAY`; đủ 234 mapping/279 ô và 108 phương trình; không còn OPEN |
| IRISK-027–IRISK-028 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro lãi suất chi tiết trong đúng PDF đã bind |
| LRISK-001/006–019 | `CLOSED_BY_E0105_DASH_ZERO_PIXEL_GEMMA4_AND_ACCOUNTING_REPLAY`; MBB/HDB/VCB/CTG và toàn bộ VIB đã khép |
| LRISK-002–LRISK-005 | `OPEN_MATERIAL_SOURCE_PRESENTATION_RESIDUAL`; bốn trục VPB lệch 6.000/275.500/6.001/275.499, không coi là làm tròn |
| LRISK-020–LRISK-021 | `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; ACB/BID không có bảng rủi ro thanh khoản chi tiết trong đúng PDF đã bind |

## Financial instruments — carrying and fair value (`FINANCIAL_INSTRUMENTS`)

- **FI-001–FI-003 — OPEN:** VPB p86, VCB p45 và CTG p51 dùng `(*)` cho các
  ô giá trị hợp lý không xác định được. Ba nhóm được giữ nguyên nguồn; không
  suy diễn 0 và không sao chép số ghi sổ.
- **FI-007–FI-011 — confirmed bound-report absences:** ACB, MBB, HDB, BID và
  VIB không có bảng chi tiết mang đồng thời hai nhánh giá trị ghi sổ/giá trị
  hợp lý. Các bảng rủi ro là matched controls thuộc family kế tiếp.

## Currency risk (`CURRENCY_RISK`)

Current exact-replay results: E-0101 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique currency-risk regions and
  confirms two bounded absences. Flexible axis/row order and page continuation
  are admitted; interest, liquidity and fair-value tables remain controls.
- E-0105 raises the verified denominator to 120 mappings/136 value cells and
  51 exact equations. Visible dashes become zero; the two VPB residuals of one
  remain unchanged and are explicitly bounded as presentation rounding.
- **CRISK-002/007/009 — OPEN:** only the three gold axes remain because the
  live schema has no gold branch. No gold value is collapsed into `OTHER`.

## Interest-rate risk (`INTEREST_RATE_RISK`)

Current exact-replay results: E-0102 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique interest-rate-risk regions
  and confirms two bounded absences. Flexible repricing axes/order, split-line
  labels, optional internal/external states and adjacent-page continuation are
  admitted; currency, liquidity and fair-value tables remain controls.
- E-0105 closes every gap: 234 mappings/279 value cells and 108 exact
  equations across all six present banks. VIB p62–63 uses pixel-bound Gemma 4
  as an independent challenger and 36 equations; neither OCR reader alone is
  numeric authority. VPB remains Q1/2026.
- **No IRISK entry remains OPEN.**

## Liquidity risk (`LIQUIDITY_RISK`)

Current exact-replay results: E-0103 base plus
`docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json`.

- One bank-blind whole-PDF graph finds six unique liquidity-risk regions and
  confirms two bounded absences. Combined/split overdue axes, flexible
  maturity buckets, source-row aggregation and continuation are admitted;
  currency, interest-rate and fair-value tables remain controls.
- E-0105 raises the verified denominator to 129 mappings/153 value cells and
  51 exact `assets - liabilities = net liquidity gap` equations. VIB p68–69
  is fully closed by full-table pixels, Gemma 4 challenge and 16 equations.
- **LRISK-002–LRISK-005 — OPEN:** only four material VPB residuals remain;
  they are not silently treated as rounding.

## End-period exchange rates (`EXCHANGE_RATE`)

Current exact-replay result:
`docs/experiments/E-0104-exchange-rate-8bank-codex-verified-mapping-v1.json`

- One bank-blind whole-PDF graph finds five unique exchange-rate regions at
  MBB p61, VPB p90, CTG p61, BID p35 and VIB p71 and confirms three bounded
  detailed-table absences. Flexible row order, punctuation/grouping variants,
  split period axes and document-level VND policy inheritance are admitted;
  currency-risk, interest-rate-risk, liquidity-risk and policy prose remain
  controls.
- 46 mappings/92 current-comparative value cells are independently verified.
  All 122 visible source cells remain present; VietOCR is text/geometry
  evidence only and the Paddle/native source axis plus pixels controls numbers.
- **FXRATE-001–FXRATE-015 — OPEN:** retain CNY/DKK/NZD/XAU at VPB,
  NZD/NOK/DKK/HKD/CNY/KRW/LAK at CTG and DKK/HKD/NOK/XAU at VIB. These are
  valid source rows with no live TM leaf under 5935–5945; none is discarded or
  forced into another currency.

## Project-owner catch-all and monthly-average closure (`E-0100`)

Exact-replay overlay:
`docs/experiments/E-0100-owner-adjudicated-catchall-average-closure-v1.json`

- Closes **10** prior OPEN source rows without rewriting E-0089/E-0090/E-0094/
  E-0095/E-0096: CRPE-001/002 → 1228, OACT-001 → 1239, EI-001/002 →
  derived 1267/1268, SBO-001 → 1279 and CC-001–004 → 1288.
- Catch-all rows are aggregated once with any existing same-ID row; 10
  accounting equations replay exactly. ACB's monthly values retain exact
  rational numerators/denominators rather than an untracked rounded float.

## Bank-owned pledged or discounted assets (`BANK_PLEDGED_OR_DISCOUNTED_ASSETS`)

Current exact-replay result:
`docs/experiments/E-0097-bank-pledged-assets-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique bank-owned asset region at VPB p67 and
  VIB p49. ACB/MBB/HDB/VCB/CTG/BID have no detailed note in the supplied
  reports; customer collateral and borrowing-facility text remain controls.
- Five mappings, 10 value cells and six component relations are independently
  verified. Two additional VPB printed-total reproductions are explicitly not
  accounting identities because the source presentation double-counts a parent
  and its “Trong đó” children.
- **BPA-001–BPA-003 — OPEN:** the VPB combined parent and two unsplit VIB
  use-purpose rows remain source-only rather than being forced into narrower
  security-class leaves.

## Customer collateral held (`CUSTOMER_COLLATERAL_HELD`)

Current exact-replay result:
`docs/experiments/E-0096-customer-collateral-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique customer-scoped region at VPB p67,
  VCB p47 and VIB p49. ACB/MBB/HDB/CTG/BID have no detailed customer-collateral
  note in the supplied reports.
- 15 mappings, 30 value cells and six child-to-parent equations are independently
  verified. VIB's separate TCTD and own-pledged-asset branches are excluded.
- **CC-001–CC-004 — CLOSED by E-0100:** project-owner adjudication aggregates
  each bank's source rows into 1288 `Khác` together with its pre-existing
  catch-all row, once only. Both VCB and VIB parent totals close exactly.

## State-budget obligations (`STATE_BUDGET_OBLIGATIONS`)

Current exact-replay result:
`docs/experiments/E-0095-state-budget-obligations-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p22, MBB p49,
  VPB p58, HDB p32, CTG p43, BID p26 and VIB p47; VCB has no detailed note in
  the supplied report.
- 33 mappings, 147 value cells and 37 roll-forward/net equations are
  independently verified. Thirteen visible dashes are retained as pixel-bound
  zeroes. VPB is explicitly Q1/2026.
- **SBO-001 — CLOSED by E-0100:** HDB `Tiền thuê đất` maps to 1279 `Các khoản
  phải nộp khác`; all five visible source cells are dashes and normalize to 0.

## Employee income (`EMPLOYEE_INCOME`)

Current exact-replay result:
`docs/experiments/E-0094-employee-income-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p26, VPB p66
  and VIB p49; MBB/HDB/VCB/CTG/BID have no detailed employee-income note in
  the supplied reports.
- 13 mappings, 26 value cells and 14 additive/ratio equations are independently
  verified. VPB is explicitly Q1/2026; VIB is the six-month period.
- **EI-001–EI-002 — CLOSED by E-0100:** the six-month source values are divided
  by exactly six and retained as rational numbers before mapping 1267/1268.

## Subsidiary acquisitions and disposals (`SUBSIDIARY_ACQUISITION_DISPOSAL`)

Current exact-replay result:
`docs/experiments/E-0093-subsidiary-acquisition-disposal-8bank-bound-report-absence-v1.json`

- The shared whole-PDF graph requires total consideration, cash settlement and
  cash held by the acquired/disposed subsidiary, plus period and unit evidence.
- No supplied PDF contains that complete detail table. All eight outcomes are
  bounded absences with zero mappings and zero open source rows.
- **SAD-001–SAD-008 — confirmed bound-report absences:** HDB's HDS acquisition
  narrative and CTG's investment cash-flow captions remain explicit controls;
  they do not establish the three schema rows 1256–1258.

## Cash and cash equivalents (`CASH_EQUIVALENTS`)

Current exact-replay result:
`docs/experiments/E-0092-cash-equivalents-8bank-codex-verified-mapping-v1.json`

- One whole-PDF graph finds one unique detailed region at ACB p8, MBB p50,
  VPB p66, VCB p40, CTG p47 and VIB p45. It covers total-before-components,
  combined interbank, demand/term split and optional-securities layouts.
- 31 mappings, 60 value cells and 12 accounting equations are independently
  verified, covering ReportNormId 1248–1254. No source row remains open.
- **CEQ-001–CEQ-002 — confirmed bound-report absences:** HDB and BID have no
  detailed component table; their cash-flow beginning/end balances and policy
  text remain negative controls, not mappings.

## Corporate income tax expense (`INCOME_TAX`)

Current exact-replay result:
`docs/experiments/E-0091-income-tax-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique detailed reconciliation at MBB
  p50, VPB p59 and VIB p48, using profit before tax, adjustments, taxable
  income, current tax and period/unit topology rather than bank/page routing.
- 28 mappings, 56 value cells and 20 accounting equations are independently
  verified. The mapped union covers ReportNormId 5723–5737. VPB remains Q1.
- **TAX-001 — OPEN:** VIB p48 `Điều chỉnh khác`; current-period cell is blank,
  comparative value is `163`. The source meaning is broader than 5733, so it
  remains explicit and is used only in the comparative printed-total equation.
- **TAX-002–TAX-006 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no detailed tax reconciliation; statement totals, tax-obligation
  movements and deferred-tax balances are retained as negative controls.

## Other activity income, expense and net (`OTHER_ACTIVITY`)

Current exact-replay result:
`docs/experiments/E-0090-other-activity-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique numbered note at MBB p47, VPB
  p64 and VIB p46. It accepts a net-only variant or gross income/expense
  parents with optional children and labeled/unlabeled net totals, without
  using bank, filename, note number or page as a rule.
- 23 mappings, 46 value cells and 14 accounting equations are independently
  verified. VPB's two visible asset-disposal rows are summed by authenticated
  components before one mapping to 1231.
- **OACT-001 — CLOSED by E-0100:** VPB p64 values `41 / 9` are aggregated once
  into 1239 `Khác`; the income-parent and net equations remain exact.
- **OACT-002–OACT-006 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no complete numbered detail note with period/unit axes,
  components and net total. Their KQKD totals, segment reports and explanatory
  text remain negative controls.

## Credit-risk provision expense (`CREDIT_RISK_PROVISION_EXPENSE`)

Current exact-replay result:
`docs/experiments/E-0089-credit-risk-provision-expense-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds one unique numbered detailed note at MBB
  p49, VPB p66 and VIB p47. It accepts wrapped labels, optional rows, a customer
  parent with general/specific children and an unlabeled trailing total without
  using bank, filename, note number or page as a rule.
- 15 mappings, 30 value cells and eight accounting equations are independently
  verified. Combined customer/TCTD/purchased-debt rows use existing schema
  6031/6032/6033 rather than creating duplicate concepts.
- **CRPE-001–CRPE-002 — CLOSED by E-0100:** the VPB margin/advance row
  (`- / 29.368`) and VIB trade-finance-receivable row (`- / (244)`) map to
  1228 `Dự phòng khác`; both printed family totals replay exactly.
- **CRPE-003–CRPE-007 — confirmed bound-report absences:** ACB, HDB, VCB, CTG
  and BID have no complete detailed note with period/unit axes, component rows
  and trailing total in the supplied PDFs. Statement aggregates, policies and
  explanatory mentions remain negative controls and are not relabelled.

## Capital and funds (`CAPITAL_AND_FUNDS`)

Current exact-replay result:
`docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in all eight
  reports, including geometry-selected 90-degree VietOCR rescue for rotated
  layouts; 19 near regions remain negative controls.
- ACB/MBB/VPB/HDB/VCB/CTG have 65 verified mappings, 131 numeric components and
  20 exact accounting equations. The supplied VPB PDF remains Q1/2026.
- CAF-001–CAF-008 are exact source columns without one equivalent schema leaf.
  CAF-009–CAF-010 retain BID/VIB as structure-only until an independent rotated
  numeric challenger is available; rotated VietOCR is text evidence only.

## Other payables and liabilities (`OTHER_PAYABLES_AND_LIABILITIES`)

Current exact-replay result:
`docs/experiments/E-0077-other-payables-liabilities-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in every report
  and retains 36 near controls. It requires only the owner plus internal and
  external payable branches; employee, tax, other-payable, risk, welfare,
  interest/fee and intermediate branches remain optional.
- Exact visible-pixel/source-numeric replay verifies 39 schema mappings, 78
  current/comparative components and 28 parent/detail/total equations. Two ACB
  risk-provision dashes are pixel-bound and normalized to zero.
- OPL-001–OPL-018 remain open because no exact leaf exists. Their amounts stay
  inside verified source parents/totals, and overlapping parent/detail views are
  explicitly non-additive. VPB remains the supplied Q1/2026 source.

## Issued valuable papers (`ISSUED_VALUABLE_PAPERS`)

Current exact-replay result:
`docs/experiments/E-0076-issued-valuable-papers-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in each of the
  eight reports and retains 29 near controls. It covers vertical instrument/
  tenor tables, book-value versus face-value lanes, combined promissory/bond
  parents and horizontal instrument columns without bank/page routing.
- 66 mappings, 124 value components and 36 accounting equations are
  `VERIFIED_BY_CODEX`. Four CTG dash cells are bound to exact render pixels and
  normalized to zero; empty cells are not promoted to zero.
- E-0080 closes ACB exact-five-year rows through the now-inclusive 1103/1111
  boundaries, maps MBB's printed broad tenors directly to 6009/6010 without
  inventing a narrower split, and maps BID's capital-increase bond to 1117.
  IVP-005–IVP-007 remain open only because VPB prints one whole-family tenor
  view without an instrument allocation. VPB is retained as Q1/2026.

## Entrusted/investment-risk capital (`ENTRUSTED_INVESTMENT_RISK_CAPITAL`)

Current exact-replay result:
`docs/experiments/E-0075-entrusted-investment-risk-capital-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region at MBB p43,
  VPB p56 and VIB p42, with no second complete match. It admits an aggregate
  organization/person row, a two-line ODA source and a three-line NHNN housing
  programme without bank/page routing.
- Six mappings/12 current-comparative components are `VERIFIED_BY_CODEX`; four
  printed child-to-total equations at MBB/VPB close exactly. The two small
  source-specific rows map to explicit schema catch-all 1099 rather than being
  forced into a semantically narrower currency/international-organization leaf.
- ACB/HDB/VCB/CTG/BID are absent only within the supplied reports. There are no
  open source rows for this family. VPB remains Q1/2026.

## Government and central-bank liabilities (`GOVERNMENT_NHNN_LIABILITIES`)

Current exact-replay result:
`docs/experiments/E-0074-government-nhnn-liabilities-8bank-codex-verified-mapping-v1.json`

- One shared whole-PDF graph finds exactly one complete region in each of the
  eight reports and retains 17 near regions as negative controls. It admits an
  aggregate-only table, detailed central-bank facilities, Treasury currency or
  tenor branches, repo rows and other liabilities without bank/page routing.
- 28 source mappings, 58 visible current/comparative components and 28 exact
  accounting equations are `VERIFIED_BY_CODEX`. Two source dashes omitted from
  OCR are independently bound to render pixels and normalized to zero.
- E-0080 adds broad parent 6070 for the three central-bank-loan wording
  variants and sibling 6071 for the Treasury term deposit. BID's Finance
  Ministry deposit is reclassified from catch-all 1039 to dedicated 6072.
  No source row remains open; VPB is correctly retained as Q1/2026.

## Other assets (`OTHER_ASSETS`)

Current exact-replay result:
`docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json`

- Whole-PDF fresh-VietOCR scan finds exactly one complete region in each of
  MBB p42, VPB p51–53 and VIB p39; no document has a second complete match.
  The shared graph admits split sibling notes, an explicit multi-page umbrella
  and an integrated table with subtables without bank/page routing.
- 58 source mappings, 126 visible current/comparative components and 30 exact
  accounting equations are `VERIFIED_BY_CODEX`. Five supplied reports are
  bounded absences between their long-term-investment and government-liability
  note boundaries.
- OA-001–OA-012 retain every source row that lacks an equivalent schema or has
  a broader/narrower meaning. They remain at the top of the open queue while
  the family itself is closed at its safely mapped core.

## Investment property (`INVESTMENT_PROPERTY_MOVEMENT`)

Current exact-replay result:
`docs/experiments/E-0072-investment-property-8bank-codex-verified-mapping-v1.json`

- The shared fixed-asset engine scans all 453 pages, partitions same-page
  current/comparative regions by their explicit period ends, and finds only
  MBB p41 as one unique current detailed region. The 31/12/2025 table is retained
  as comparison evidence rather than mixed into the 30/06/2026 values.
- Nine source mappings and eleven visible roll-forward, asset-column and
  carrying-value equations are `VERIFIED_BY_CODEX`. MBB's `Giá trị hao mòn`
  wording is accepted as the accumulated-depreciation branch. The visible DASH
  in current cost increases is pixel-bound and normalized to zero.
- IP-001–IP-007 close the other seven outcomes only for these supplied PDFs.
  Balance-sheet lines, accounting policies, cash-flow rows and combined
  fixed-asset/investment-property expenses remain negative controls. No source
  row in the verified MBB region remains open.

## Intangible fixed assets (`INTANGIBLE_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0071-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json`

- One shared fixed-asset graph scans all 453 pages and finds unique current-period
  regions at MBB p39, VPB p50 and VIB p38; MBB p40 remains comparison-only.
- 32 source mappings and 12 visible roll-forward/carrying-value equations are
  `VERIFIED_BY_CODEX`. ReportNormId 6068 groups gross-cost decreases 921–927;
  new ReportNormId 6069 preserves the distinct fully-amortized-but-still-in-use
  disclosure at VPB/VIB rather than forcing it into another movement row.
- IFA-001–IFA-005 close the five no-region outcomes only for the supplied PDFs.
  IFA-006 closes the schema gap. No intangible-fixed-asset row remains open;
  VPB keeps its Q1/2026 source-period caveat.

## Customer-loan geography (`LOAN_GEOGRAPHIC_CLASSIFICATION`)

Base exact-replay result:
`docs/experiments/E-0065-loan-geography-8bank-codex-verified-mapping-v1.json`

Project-owner absence closure:
`docs/experiments/E-0067D-loan-geography-project-owner-absence-closure-v1.json`

- One bank-blind graph scans all 453 pages and combines the geographic
  concentration heading with an exact customer-loan axis before reading the
  domestic/foreign structure. It supports geography by rows or columns and
  consecutive-period continuation, while retaining broader total-loan tables
  and geographic segment reports as negative controls.
- MBB p52 and VIB p53–54 are the only exact customer-loan populations. Four
  source rows (5752/765 for each bank), six period-value cells and three
  domestic-plus-foreign equations are `VERIFIED_BY_CODEX`. VIB's two visible
  foreign dashes stay typed `DASH` before zero normalization.
- LG-001–LG-006 are closed as bound-report absences for this exact family.
  ACB/VPB/HDB/CTG/BID retain their mechanically broader total-loan geography
  equations as negative controls; VCB retains its p42 segment-report matrix.
  None is silently narrowed, promoted, or treated as absent in another filing.

## Deposits at and loans to other credit institutions (`INTERBANK_DEPOSITS_AND_LOANS`)

Current exact-replay result:
`docs/experiments/E-0062-interbank-deposits-loans-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages, binds the first family owner through
  demand/term deposits, currency children, interbank loans and the last printed
  subtotal or family total. It admits `cho vay`/`vay`, optional deposit-parent
  labels, gold+foreign-currency wording, non-additive discount details and an
  explicit document-level unit declaration.
- ACB p16, MBB p30, VPB p39, CTG p41, BID p25 and VIB p32 are unique complete
  clusters. 63 source rows are `VERIFIED_BY_CODEX`; 23 accounting equations
  close exactly. Three ACB visible dashes remain typed `DASH` before the
  project-owner-approved zero normalization. VPB retains its Q1/2026 caveat.
- HDB/VCB are now confirmed not present in the bound reports by the project
  owner: both supplied note sections begin at trading securities. Their totals
  and foreign-exchange/fair-value controls remain negative controls.

## Deposits at central banks (`CENTRAL_BANK_DEPOSITS`)

Current exact-replay result:
`docs/experiments/E-0061-central-bank-deposits-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and binds the first family owner,
  central-bank parent, required currency children and first trailing two-period
  total. It records horizontal row/period layout and stops before reserve-ratio
  tables or the next TM family.
- MBB p30, VPB p38 and VIB p31 are the only unique complete detailed clusters.
  Ten source rows are `VERIFIED_BY_CODEX`, and four current-period equations
  close exactly. VPB retains its Q1/2026 source-period caveat.
- MBB's Laos and Cambodia rows are aggregated into ReportNormId 574 `Tiền gửi
  khác`: `934.855 + 1.213.504 = 2.148.359`; together with Vietnam deposits,
  `25.269.011 + 2.148.359 = 27.417.370`. The project owner
  confirmed that ACB/HDB/VCB/CTG/BID do not contain this TM family in the bound
  PDFs, based on each report's first TM family boundary; balance-sheet totals
  do not contradict that bounded note-level absence.

## Cash and precious metals (`CASH_PRECIOUS_METALS`)

Current exact-replay result:
`docs/experiments/E-0060-cash-precious-metals-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and requires a short owner, VND and
  foreign-currency cash children, visible period/unit axes and a trailing total.
  It finds exactly one complete region for MBB p30, VPB p38 and VIB p31.
- 12 source rows are `VERIFIED_BY_CODEX`: ReportNormId 562, 563, 565 and the
  exact family total 561 for each complete region. Three current-period
  `VND + foreign + monetary gold = total` equations close exactly.
- The project owner confirmed ACB/HDB/VCB/CTG/BID do not contain this TM family
  in the bound PDFs: ACB's notes start at the interbank family, while the other
  four start at trading securities. Balance-sheet totals and cash-flow/risk
  disclosures remain negative controls rather than manufactured note mappings.
- VPB retains its Q1/2026 source-period caveat.

## Trading securities (`TRADING_SECURITIES`)

Current exact-replay result:
`docs/experiments/E-0059-trading-securities-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages. It finds one unique trading region
  for ACB, MBB, VPB, HDB, VCB, CTG and BID, while rejecting accounting-policy
  prose, provision roll-forwards and investment securities as sibling families.
- 58 source rows are `VERIFIED_BY_CODEX`; 20 parent/child and
  gross/provision/net equations close exactly. First/last cluster items, PDF row
  order, period/unit columns and parent-total placement remain explicit.
- MBB uses the listed/unlisted branch. The other six mapped banks use the issuer
  branch. Unlabeled gross rows are admitted only when topology and the full
  accounting equation both agree.
- VIB p36 AFS was deliberately excluded here and is now resolved by E-0067 as
  the investment-securities family. VPB retains its Q1/2026 source-period caveat.

## Investment securities (`INVESTMENT_SECURITIES`)

Base exact-replay result:
`docs/experiments/E-0067-investment-securities-8bank-codex-verified-mapping-v1.json`

Project-owner closure:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- One bank-blind graph scans all 453 pages and finds exactly one complete
  investment region per PDF. It supports explicit or implicit family owners,
  AFS/HTM branches, provision and quality alternate views, VAMC, two-page
  continuation and first/last/next-family boundaries.
- ACB p19, MBB p35–36, VPB p47–48, HDB p29, VCB p32, CTG p40, BID p23 and
  VIB p36 now provide 99 verified source mappings/198 period cells; 39 visible
  parent-child or gross-provision-net equations close exactly.
- IS-001 is closed by the explicit document-level `Triệu VND` statement on BID
  p13 of the same PDF. IS-002 is closed by retaining both VIB source components
  and proving `5.894.320 + 32.879.230 = 38.773.550` and
  `12.104.102 + 28.252.422 = 40.356.524` before mapping one aggregate to 808.

## Other long-term investments (`OTHER_LONG_TERM_INVESTMENTS`)

Current exact-replay result:
`docs/experiments/E-0068-long-term-investments-8bank-codex-verified-mapping-v1.json`

- One bank-blind graph scans all 453 pages and finds exactly one complete
  region in each PDF: ACB p19, MBB p36, VPB p48, HDB p30, VCB p33, CTG p40,
  BID p24 and VIB p36. Optional joint-venture, associate, other-investment,
  organization/project and fund branches may be absent or reordered.
- All 29 reviewed source mappings and 58 period cells are
  `VERIFIED_BY_CODEX`; nine visible accounting equations close exactly. The
  HDB current associate DASH remains typed before zero normalization. VPB
  remains explicitly Q1/2026.
- Schema gaps for joint ventures and associates are closed by ReportNormId
  6066 and 6067 under parent 862. No source row from the bounded eight regions
  remains in the open queue; detailed organization rows are retained as
  corroboration and are not double-counted with their mapped parent.

## Tangible fixed assets (`TANGIBLE_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0069-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json`

- One bank-blind owner/cost/accumulated-depreciation/carrying-value graph scans
  all 453 pages and finds unique detailed regions at MBB p37, VPB p49 and VIB
  p37. MBB p38 is retained only as the prior-period continuation control.
- All 35 reviewed mappings and 12 visible roll-forward/carrying-value equations
  are `VERIFIED_BY_CODEX`. VIB's rotated page uses fresh same-model VietOCR for
  text and an independently sealed rotated PP-OCRv6 numeric challenger; four
  disagreements from the original rotated source OCR are resolved by pixels and
  exact accounting closure rather than semantic guessing.
- ACB/HDB/VCB/CTG/BID are confirmed absent only in the bound reports. Main
  statement balances and accounting-policy prose remain negative controls.
  There is no open mapping item for this family. VPB remains Q1/2026.

## Leased fixed assets (`LEASED_FIXED_ASSETS_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0070-leased-fixed-assets-8bank-bound-report-absence-v1.json`

- The shared fixed-asset graph scans all 453 pages and finds no complete or
  near-complete 896–912 region in ACB, MBB, VPB, HDB, VCB, CTG, BID or VIB.
- All eight dispositions are `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; this is
  bounded to the supplied PDFs and is not a broader bank/document absence
  claim.
- Twenty-four finance-lease company, policy, lending and income lines remain
  negative controls. No source row is open and no mapping is manufactured.

## Project-owner TM adjudications

Exact-replay decision artifact:
`docs/experiments/E-0067A-project-owner-tm-adjudications-v1.json`

- CBD-001/CBD-002 close into one ReportNormId 574 aggregate with exact source
  components and arithmetic retained.
- IDL-001/IDL-002 and DFI-001 close as bounded-report absences; the confirmation
  does not assert absence in another filing or bank.
- VIB p36 is explicitly confirmed under 804 → 805, with the live 804 children
  805/829/853/859 and last descendant 861; it is not trading 592.

## Loan-quality margin normalization

Exact-replay normalized result:
`docs/experiments/E-0067B-loan-quality-margin-separation-project-owner-v1.json`

- The already registered template identity 1944 is reused instead of allocating
  another duplicate-name ID. In this bounded context it is a direct child of
  family 746 and represents `Cho vay giao dịch ký quỹ và ứng trước tiền bán
  chứng khoán` independently from the five quality grades.
- ACB p18 and VPB p42 expose the row after the five-grade core, so ReportNormId
  747 remains unchanged and the visible row maps to 1944.
- MBB p31 exposes the same population as 5746 `Trong đó` under 747. The source
  disclosure is retained as a non-output bridge; normalized 747 is reduced by
  exactly 5746 on both axes and the same amount is emitted once as 1944.
- All 18 per-axis family/split equations close; no 5746+1944 double count is
  permitted. This closes the two former outside-core ACB/VPB populations.

## Customer-deposit and investment owner closure

Exact-replay result:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- CD-001/CD-002: the two-state-member-or-more labels at VPB p55 and VIB p42
  map to the owner-confirmed schema 770 name `Công ty TNHH MTV (hoặc trên MTV)
  vốn nhà nước trên 50%`; values `64.165` and `174` remain separately bound.
- IS-001: BID p23 inherits `Triệu VND` only from the visible document-level
  declaration at p13 of that same PDF. Fourteen mappings, 28 cells and ten
  accounting equations are independently replayed; the visible comparative
  dash remains typed before zero normalization.
- IS-002: VIB p36 retains the bond and certificate-of-deposit components and
  maps their per-period sums once to 808. No component is dropped or emitted a
  second time.

## Customer deposit (`CUSTOMER_DEPOSIT_CLASSIFICATION`)

Base exact-replay result:
`docs/experiments/E-0058-customer-deposit-8bank-codex-verified-mapping-v1.json`

Project-owner closure:
`docs/experiments/E-0067C-customer-deposit-investment-owner-closure-v1.json`

- Một graph bank-blind quét đủ 453 trang và tìm đúng một vùng hoàn chỉnh trong
  mỗi PDF. Biên đầu/cuối, thứ tự hàng nguồn, bố cục ngang/dọc, kỳ và trục tiền tệ
  đều được giữ lại.
- 120 dòng được xác minh; 43 phương trình cha = con, tổng cột và tổng
  bảng đóng chính xác. Cột tổng và cột phần trăm chỉ là đối chứng khi không phải
  một khoản mục độc lập.
- VIB p42 dòng `Công ty Nhà nước`: VietOCR Transformer đọc thiếu chữ số đầu
  (`3.034.518`), còn pixel PDF và numeric challenger PP-OCRv6 cùng cho
  `13.034.518`; kết quả dùng `13.034.518` và lưu nguyên disagreement.
- CD-001/CD-002 đã đóng: hai dòng VPB/VIB cùng map vào schema 770 theo quyết
  định của chủ dự án, giữ nguyên giá trị nguồn `64.165` và `174`. Không còn
  dòng nguồn chưa map trong family; VPB vẫn giữ đúng kỳ nguồn Q1/2026.

## Provision movement (`PROVISION_MOVEMENT_ROLLFORWARD`)

Current exact-replay result:
`docs/experiments/E-0057-provision-movement-8bank-codex-verified-mapping-v1.json`

- ACB p18, MBB p34, HDB p28, VCB p31, CTG p39, BID p23 và VIB p34:
  `VERIFIED_BY_CODEX` cho kỳ hiện tại Q2/2026.
- VPB p45: `VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT` cho kỳ
  01/01–31/03/2026. Ba lane chung/cụ thể/margin-ứng trước và toàn bộ movement
  hiện hữu đều đã map; chỉ nguồn Q2/2026 còn thiếu.
- MBB chỉ dùng cột `Tổng cộng`; các cột Việt Nam/nước ngoài là đối chứng.
  Kỳ so sánh của mọi bank không được dùng làm mapping authority.

## OCR and numeric evidence policy

- Vietnamese semantic anchors come from the fresh VietOCR Transformer cache;
  accentless normalization and bounded edit-distance matching only locate a
  candidate graph.  They never decide the mapping by themselves.
- PP-OCRv6 is an authenticated geometry/provider and may contribute an
  independent numeric proposal.  It is **not**, by itself, final numeric truth.
- Gemma is permitted only as a bounded rescue/challenger on a fixed difficult
  crop.  A Gemma answer cannot silently replace a digit, sign, decimal separator,
  DASH, blank, or missing cell and cannot become automatic numeric authority.
- An accepted number must remain bound to the exact crop and typed lane, survive
  independent digit/sign/DASH review, and satisfy the applicable row/total/
  roll-forward accounting equations.  Disagreement without decisive pixel and
  accounting evidence remains `UNRESOLVED`.

## Loan type (`LOAN_TYPE_CLASSIFICATION`)

Historical pre-adjudication result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v1.json`

Current exact-replay result:
`docs/experiments/E-0054-loan-type-8bank-codex-verified-mapping-v2.json`

Result ID:
`lt8bcv2:result:f5765671514ac40550fe349633b2d95b693537d65e18e91101434904d3d652dd`

### LT-001 — ACB — government-directed lending

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 17 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cho vay theo chỉ định của Chính phủ`
- Visible source values: `-` / `-`; raw source status remains `DASH`.
- Project-owner decision: append an exact schema child for the visible label and
  normalize each independently reviewed visible DASH to numeric `0` for the
  template without erasing the raw DASH provenance.
- Accepted schema: ReportNormId `6057` (`Cho vay theo chỉ định của Chính phủ`),
  parent `717`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LT-002 — VPB — other credit

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 42 / customer-loan type analysis
- Owner / source label: `Cho vay khách hàng` / `Cấp tín dụng khác`
- Visible values: `72.360.147 | 6,95% | 73.847.196 | 7,82%`
- Accepted schema: ReportNormId `726` (`Cho vay khác`).
- Project-owner decision: within this exact `Cho vay khách hàng` type-analysis
  graph, `Cấp tín dụng khác` is the source variant of `Cho vay khác`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

## Loan industry (`LOAN_INDUSTRY_CLASSIFICATION`)

Source scan: `lifdsv1:scan:a0b560c0ff0fb07fff7e49e4c9b38c2b3f9baa8aefb9d911f37d01a920b54a11`

Historical pre-adjudication result ID:
`li8bcv1:result:a7435794e8639f9aa53ada040d13abddf966b91ab839a9aa1391bf2cdba52c58`

Current exact-replay result:
`docs/experiments/E-0055-loan-industry-8bank-codex-verified-mapping-v2.json`

Current result ID:
`li8bcv2:result:3ac4ba987593baf8e0a03c3a1f2414dacf1008df38fc890519d72d2c9160cbdb`

Exact-replay builder:
`scripts/experiments/build_loan_industry_8bank_codex_verified_mapping_v1.py`

### LI-001 — ACB — industry family not present in bound report

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 33 physical pages, fresh VietOCR line axis
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Machine scan: no region survives the full-PDF parent/child-pair search plus
  period/unit/total/accounting checks; trying a smaller one-child graph does not
  manufacture an occurrence.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; this is not a claim about
  other ACB reports or the broader corpus.

### LI-002 — MBB — transport and storage

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải, Kho bãi`
- Visible values: `34.348.471 | 2,80% | 29.961.714 | 2,76%`
- Accepted schema: ReportNormId `736` (`Vận tải kho bãi và thông tin liên lạc`).
- Project-owner decision: `Vận tải, Kho bãi` is an admitted source variant of
  the combined schema concept; the separately visible information/communication
  row remains mapped to its own ReportNormId `740`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-003 — MBB — foreign branch population

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Visible values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Accepted schema: new ReportNormId `6058`, exact visible-label child under
  ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-004 — VPB — transport and storage

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Vận tải kho bãi`
- Visible values: `12.790.970 | 1,23% | 12.417.698 | 1,32%`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-005 — VPB — public administration/defence/social security

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Hoạt động của Đảng cộng sản, tổ chức chính trị-xã hội, quản lý Nhà nước, an ninh quốc phòng, bảo đảm xã hội bắt buộc`
- Visible values: `5.892 | 0,00% | 14.165 | 0,00%`
- Accepted schema: ReportNormId `745` (`Các ngành nghề khác`).
- Project-owner decision: this immaterial row is grouped into the explicit
  catch-all; it is not mapped to ReportNormId `744`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-006 — VPB — personal housing loan population

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / branch: 44 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Cho vay cá nhân để mua nhà ở, nhận quyền sử dụng đất để xây nhà ở`
- Visible values: `139.410.297 | 13,39% | 130.375.600 | 13,81%`
- Accepted schema: new ReportNormId `6059`, exact visible-label child under
  ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-007 — HDB — transport and storage

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 27 / `Phân tích dư nợ cho vay theo ngành nghề đăng ký kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `26.889.305 | 25.142.909`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-008 — VCB — industry family not present in bound report

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 55 physical pages, fresh VietOCR line axis (including terminal
  geometry-only pages without inherited transcript)
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry; the visible loan analysis on page 31 is by maturity, not industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; no broader-corpus absence
  claim is made.

### LI-009 — CTG — industry family not present in bound report

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Scan scope: all 61 physical pages, fresh VietOCR line axis
- Target family: ReportNormId `727` — `Phân tích theo ngành nghề kinh doanh`.
- Project-owner confirmation: this PDF does not disclose loan analysis by
  industry; the visible loan analysis on page 39 is by original loan tenor, not
  industry.
- Status: `CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT`; no broader-corpus absence
  claim is made.

### LI-010 — BID — broad services

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 22 / `Phân tích dư nợ cho vay theo ngành`
- Source label: `Dịch vụ`
- Visible values: `534.960.928 | 444.190.319`
- Accepted schema: new ReportNormId `6060` (`Dịch vụ`), exact visible-label
  child under ReportNormId `727`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

### LI-011 — VIB — transport and storage

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / branch: 33 / `Phân tích dư nợ theo ngành nghề kinh doanh`
- Source label: `Vận tải kho bãi`
- Visible values: `11.771.262 | 2,96% | 12.478.803 | 3,27%`
- Accepted schema: ReportNormId `736`.
- Status: `RESOLVED_VERIFIED_BY_CODEX`.

## Loan enterprise/customer type (`LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION`)

Fresh full-document scan:
`lefdsv1:scan:a8d2c5c3b49051773ca518a793a407ace5d9d9e2397675398f20f703143958d6`

Current exact-replay result:
`docs/experiments/E-0056-loan-enterprise-8bank-codex-verified-mapping-v1.json`

Result ID:
`le8bcv1:result:b6b858689f966259c4b2c8b4ea91bcc7c6bec906ce3cd060df9ebcb3eb5f27a9`

The enterprise/legal-form matcher found one unique complete region in MBB p32,
VPB p43, HDB p26, and VIB p34.  The other four PDFs do not expose that legal-form
branch, but each contains a distinct headerless **loan-type** region directly
under `Cho vay khách hàng`; those regions are already found and verified by the
owner-direct E-0054 graph.  They are not forced into the wrong schema parent
766.  In E-0056, 44 source rows are `VERIFIED_BY_CODEX`, including the exact
foreign-branch population concept 6058; no schema-semantic row remains
unresolved.  Six non-additive source group/total equations remain explicit.

### LE-001 — ACB — headerless owner-direct loan-type region

- Report: `vietstock_bctc/ACB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 17, directly below `4. CHO VAY KHÁCH HÀNG:`.
- No branch title `Phân tích theo loại hình cho vay` is required.  The generic
  owner-direct graph binds the two period axes, unit scope, seven visible child
  roles and the closing total.
- Verified children include ReportNormIds `718`, `722`, `719`, `723`, `725`,
  `721`, and `724`; government-directed lending is separately mapped to `6057`.
- Resolving result: E-0054 V2
  `lt8bcv2:result:f5765671514ac40550fe349633b2d95b693537d65e18e91101434904d3d652dd`.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-002 — MBB — source-only “Cho vay các TCKT” group parent

- Report: `vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 32 / enterprise or customer-type analysis
- Pixel text / accentless: `Cho vay các TCKT` / `cho vay cac tckt`
- Visible values: `721.497.618 | 58,79% | 621.056.253 | 57,28%`
- Candidate schema: no new leaf is needed.  The visible legal-form descendants
  remain the higher-resolution representation.
- Review status: `RESOLVED_SOURCE_ONLY_GRAPH_NODE_RETAINED_FOR_CHECK`
- Machine reason: `SOURCE_ONLY_GROUP_PARENT_WOULD_DOUBLE_COUNT_LEGAL_FORM_CHILDREN`
- Reason: its visible legal-form descendants already partition and sum to this
  parent. Mapping both parent and descendants would double count.
- Resolution: retained as a source-only graph parent; its two-axis parent-child
  equation is replayed and closed in the E-0056 result.

### LE-003 — MBB — source-only “Cho vay cá nhân” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay cá nhân` / `cho vay ca nhan`
- Visible values: `478.995.719 | 39,01% | 437.686.958 | 40,38%`
- Accepted schema equivalence: ReportNormId `780` (`Hộ kinh doanh, cá nhân`).
- Review status: `RESOLVED_NON_ADDITIVE_SCHEMA_EQUIVALENCE`
- Resolution: `Cho vay cá nhân` and its immediately following 780 child have
  identical four-lane values.  E-0056 records the parent→780 equivalence but
  exports the numeric amount once only; parent and child must never be summed.

### LE-004 — MBB — source-only “Cho vay khác” group parent

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel text / accentless: `Cho vay khác` / `cho vay khac`
- Visible values: `937.382 | 0,08% | 904.945 | 0,09%`
- Accepted aggregate equivalence: ReportNormId `782` (`Khác`).
- Review status: `RESOLVED_NON_ADDITIVE_SCHEMA_EQUIVALENCE`
- Resolution: the source parent is explicitly associated with 782 as the
  aggregate/catch-all view, while its two visible children remain available as
  the detailed view.  E-0056 marks the relation non-additive, so an export must
  choose the aggregate or its descendants and cannot count both.

### LE-005 — MBB — foreign-branch population and its two children

- Report / physical page: MBB consolidated Q2 2026 / 32
- Pixel parent: `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`
- Parent values: `9.295.704 | 0,75% | 9.330.629 | 0,86%`
- Pixel children: `Cho vay Doanh nghiệp` = `2.121.916 / 2.176.885`;
  `Cho vay cá nhân` = `7.173.788 / 7.153.744`
- Accepted schema: ReportNormId `6058`, whose canonical label is already exactly
  `Cho vay tại Chi nhánh và ngân hàng con nước ngoài`.
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Resolution: the project reuses the existing exact concept rather than creating
  a duplicate ID merely because MBB repeats it in another source presentation.
  E-0056 maps the row once, preserves its two source children and parent-child
  equation, and marks the group relation non-additive.

### LE-006 — VPB — “Khác” monetary cells not attached by semantic geometry

- Report: `vietstock_bctc/VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf`
- Physical page / family: 43 / enterprise or customer-type analysis
- Pixel text / accentless: `Khác` / `khac`
- Raw VietOCR values: `2 | 0,00 | 2 | 0,00`
- Graph values: `missing | 0,00 | missing | 0,00`
- Candidate schema: ReportNormId `782`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `VISIBLE_MONETARY_CELLS_OUTSIDE_CURRENT_ROW_GEOMETRY_BAND`
- Reason: pixels clearly show both monetary values, but the current generic row
  association did not bind them. No zero/missing imputation is allowed.
- Resolution: exact visible monetary cells `2 / 2` are pixel-bound, close the
  accounting graph, and map to ReportNormId `782` (`Khác`).

### LE-007 — HDB — “Doanh nghiệp tư nhân” dash/current and 27/comparative

- Report: `vietstock_bctc/HDB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 26 / enterprise or customer-type analysis
- Pixel text / accentless: `Doanh nghiệp tư nhân` / `doanh nghiep tu nhan`
- Pixel values: `- | 27` (`DASH`, not zero or missing)
- Fresh semantic graph values: `missing | 27`
- Candidate schema: ReportNormId `774`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `DASH_PIXEL_NOT_PRESENT_IN_FRESH_SEMANTIC_LINE_AXIS`
- Reason: the row identity is structurally clear, but the numeric verifier must
  preserve a typed dash rather than treating the absent OCR token as zero.
- Resolution: the raw value remains typed `DASH`, while its explicit normalized
  numeric interpretation is `0`; the comparative `27` is preserved. The row maps
  to ReportNormId `774`.

### LE-008 — VCB — headerless owner-direct loan-type region

- Report: `vietstock_bctc/VCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 30, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `722`, `719`, `723`, and `721` without
  requiring a printed branch title.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-009 — CTG — headerless owner-direct loan-type region

- Report: `vietstock_bctc/CTG/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 38, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `722`, `719`, `723`, `725`, `721`, and
  `726`; the visible DASH in `Cho vay khác` remains typed DASH with numeric
  interpretation zero.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-010 — BID — headerless owner-direct loan-type region

- Report: `vietstock_bctc/BID/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Exact region: physical page 22, owner-direct rows below `Cho vay khách hàng`.
- E-0054 verifies ReportNormIds `718`, `721`, `722`, `719`, and `723` plus the
  exact two-axis total.
- Review status: `RESOLVED_VERIFIED_BY_CODEX_HEADERLESS_OWNER_DIRECT_VARIANT`.

### LE-011 — VIB — VietOCR dropped one digit in “Công ty cổ phần khác”

- Report: `vietstock_bctc/VIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf`
- Physical page / family: 34 / enterprise or customer-type analysis
- Label / accentless: `Công ty cổ phần khác` / `cong ty co phan khac`
- Raw VietOCR current value: `97.043.85`
- Independent PP-OCRv6 proposal: `97.043.851` with recognition score
  `0.9999531507492065`; this is corroborating numeric evidence, not sole truth.
- Independent pixel transcription: `97.043.851`
- Other visible lanes: `24,44% | 77.496.641 | 20,29%`
- Candidate schema: ReportNormId `773`
- Review status: `RESOLVED_VERIFIED_BY_CODEX`
- Machine reason: `FRESH_VIETOCR_DIGIT_OMISSION_BREAKS_CURRENT_PERIOD_ACCOUNTING_CLOSURE`
- Reason: the pixel value closes the printed total `397.083.447`; the raw OCR
  value does not. The correction must come from independent pixel-bound numeric
  verification, never silent string repair.
- Resolution: the exact crop-bound pixel value `97.043.851` is retained alongside
  the raw Transformer proposal and maps to ReportNormId `773`; total closure is exact.

## E-0066 — bounded whole-PDF non-observation controls for `Hoạt động mua nợ`

These four entries satisfy the ledger requirement for every no-complete-region
outcome. They are not open mappings: the supplied PDFs were scanned completely,
and the family is recorded as absent only inside that fixed source scope.

### PD-001 — ACB — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no region contains the owner `Hoạt động mua nợ`, the
  balance rows, the principal/interest detail and the next-family boundary.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-002 — VCB — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-003 — CTG — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

### PD-004 — BID — no complete purchased-debt region

- Review status: `RESOLVED_BOUNDED_NOT_OBSERVED_IN_SUPPLIED_PDF`
- Whole-PDF outcome: no complete owner→balance→principal/interest cluster.
- Mapping outcome: no source row to map; no broad-corpus absence claim.

Resolving result: E-0066
`e0066:result:79e15086c88ca9283d450955da737a620012679f36071e39dce9a63962c76a3b`.

## Append policy

Every later family appends entries here when a source row or complete region is
not safely mapped.  Resolved entries remain as history after an independently
replayed mapping supersedes them; the resolving result ID and commit are added
to the entry.  The following cases must be retained explicitly rather than
silently dropped:

- a visible source row with no exact schema concept;
- a plausible schema candidate whose scope is narrower, broader, or otherwise
  different from the source row;
- a VietOCR/pixel disagreement that can affect identity or numeric closure;
- a source-only parent, subtotal, optional branch, or continuation that is
  needed for graph/accounting closure but is not itself mapped;
- multiple structurally plausible regions in the same PDF;
- a whole-PDF scan with no complete region under the current contract.

For each future entry, use status `OPEN`, `NEEDS_PIXEL_REVIEW`,
`NEEDS_SCHEMA_DECISION`, `NEEDS_ACCOUNTING_RECONCILIATION`, or `RESOLVED`, in
addition to the exact machine reason.  `RESOLVED` entries remain in the file as
an audit trail and include the independent verification result ID and commit.
