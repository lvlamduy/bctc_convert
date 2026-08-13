# VietOCR Transformer vs Seq2Seq — quyết định semantic reader

## Kết luận

Chọn **official VietOCR 0.3.13 VGG Transformer** (`vgg19_bn_transformer`) làm semantic text proposal reader. Giữ **VGG Seq2Seq** ở chế độ benchmark-only. Không dùng ONNX.

Kết quả 387 all-LINE corroborates quyết định này: Transformer có transcript/core-role accuracy và CER/WER tốt hơn rõ rệt, dù Seq2Seq nhanh hơn và có một số thắng cục bộ. VietOCR chỉ đọc chữ tiếng Việt; V3/PP-OCR tiếp tục là authority cho geometry, source locator, số, kỳ, dấu số và các evidence gốc. Unit vẫn phải được xác nhận từ context/topology, không được promote chỉ từ một chuỗi OCR.

## Benchmark chính đã freeze

- Panel: SHB p24, NVB p32, NVB p31, BVB p27, BAB p44.
- Denominator: 5 trang, 387/387 authenticated LINE crops, 52 dòng truth UTF-8/NFC, 3 positive family cases, 3 hard controls.
- Truth chỉ được tạo/join sau khi cả hai output và run manifest đã đóng băng.
- Crop manifest: `61c31e8ab6f7c3c1572ada66f0d55de690393bfb2cdfc90749200c5543c4b820`.
- Reader request: `f69829bfae6e61d5794ff67a582b57abe2e75a2f917098e6529ecd579819d334`.
- Transformer result/run: `4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1` / `6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7`.
- Seq2Seq result/run: `5c21ed137774262f770a8b2b28287efb88e952e6e2e640776066cc1e5031170f` / `8c6c32a2845998d28bff47ff637105f2dc5b78dc79b7fc24b1445b4e702f60fa`.

| Chỉ số | Transformer | Seq2Seq |
|---|---:|---:|
| Exact Vietnamese transcript | 42/52 | 38/52 |
| Exact core semantic role | 32/41 | 27/41 |
| Exact unit label | 10/11 | 11/11 |
| Correct parsed unit | 11/11 | 11/11 |
| Strict positive topology | 1/3 | 1/3 |
| Accentless topology shortlist (diagnostic-only) | 3/3 | 3/3 |
| Hard-control false merge | 0/3 | 0/3 |
| Hard-control false accept | 0/3 | 0/3 |
| Hard-control accentless false-merge shortlist | 0/3 | 0/3 |
| CER | 2.030% | 3.205% |
| WER | 5.263% | 10.088% |
| Empty / suffix truncation / insertion proxy | 0 / 0 / 0 | 0 / 0 / 0 |
| Total wall time | 22.808 s | 6.857 s |

Seq2Seq nhanh hơn khoảng 3.33× trên batch này, nhưng tốc độ chỉ là tie-break sau semantic accuracy và control safety. Theo ngân hàng, Seq2Seq bằng Transformer ở SHB/BVB, tốt hơn 1 exact line ở BAB, nhưng kém 5 exact lines và tăng CER 3.133 điểm phần trăm ở NVB.

Key bỏ dấu phục hồi được cả 3/3 positive topology thành shortlist ở cả hai model và không shortlist nhầm 3 controls. Đây chỉ là evidence về recall: strict acceptance vẫn là 1/3, vì key bỏ dấu một mình không có quyền accept. Downstream có thể promote một candidate duy nhất, không collision chỉ khi có đủ independent topology evidence.

### Exact family-role outcomes

| Case | Transformer | Seq2Seq | Kết quả strict/control |
|---|---|---|---|
| SHB24 loan maturity | Owner, branch, 2 units, `Nợ ngắn hạn / Nợ trung hạn / Nợ dài hạn` đều đúng | Tất cả đều đúng | Cả hai 1 strict positive |
| NVB32 loan quality | Bốn nhóm đầu đúng; `Nợ có khả năng mất vôn` | `tiêu chuần`, `chủ y`, `tiểu chuẩn`, `nghi ngơ`, `mất vôn` | Cả hai unresolved, không strict accept |
| NVB32 loan maturity | Branch `...cho vay góc`; unit `Triệu đông`; `Nơ ngắn hạn` | Branch phần lớn mất dấu; `Nơ ngần hạn`; `Nợ dai hạn` | Cả hai unresolved, không strict accept |
| NVB31 interbank quality control | Target owner không xuất hiện; owner OCR thành `TIÊN...`; branch còn đúng | Target owner không xuất hiện; owner `TIÊN...`; branch sai `tiên gửi` và mất dấu `:` | 0 false merge, 0 false accept |
| BVB27 purchased-debt quality control | Nhận đúng các role hiện diện nhưng owner là `Hoạt động mua nợ`, chỉ có 3/5 nhóm | Tương tự | 0 false merge, 0 false accept |
| BAB44 liquidity maturity-axis control | Có lỗi cục bộ `Rùi ro`, `Tổng nợ phải trà` | Có lỗi cục bộ `Quả hạn`; các role kia tốt hơn | 0 false merge, 0 false accept; maturity là AXIS, không phải loan rows |

Toàn bộ 52 transcript, prediction và line locator nằm trong file TXT hậu-kiểm; JSON giữ cả line metrics, case topology, per-bank delta và timing.

## Regression panel 106 crops: BVB/CTG/BAB

Đây là replay bổ sung trên batch cũ gồm 106 selected LINE/strict-union crops, không thay denominator 387 chính.

- Transformer result/run: `0f421e9a16d521ec5ed7267ecd94aa0e1372638908f75b0320481461a3d025a7` / `37d402d3ff6eed99c8c276b97664263f79c87ff05f4a9ec0a92001aba872448e`.
- Seq2Seq result/run: `f837c7eec0d60d6847c85113fd16856f3207eadbf64f4f2310a742047f07a9a9` / `b519b1a4f776d4bfa7406673fa0b27521916c46dd53b2e0088c8a6551671bc18`.
- Total wall time: Transformer 14.538 s; Seq2Seq 4.781 s (Seq2Seq nhanh khoảng 3.04×).

Hand-audit lại đúng các role đã khóa cho family cho kết quả:

- BVB p25 loan quality: cả hai nhận đúng branch và đủ 5 ordered children.
- CTG p39 loan quality: Transformer nhận đúng branch và đủ 5 children; Seq2Seq sai `Nơ đủ tiêu chuẩn`, `Nơ cần chủ ý`, `Nợ dưới tiểu chuẩn`.
- CTG p39 loan maturity: Transformer sai `Nợi ngắn hạn`; Seq2Seq sai `Nợ ngăn hạn`; cả hai để unresolved.
- BVB p27 purchased-debt và BAB p44 liquidity controls: không tạo customer-loan family false merge/accept.

Vì vậy strict positive là Transformer 2/3 và Seq2Seq 1/3; hard-control false merge/accept vẫn 0/2. Formal postjoin cũ cũng đã ghi Transformer strict 2/3, contextual-presentation 3/3, controls 0/2.

## MBB Q2 p31 — counterexample được giữ lại

Panel MBB gồm 50 crops. Đây là counterexample quan trọng, không được che đi:

- Transformer result/run: `7a52a22593137066c6ac7780cc9cd97f6ef1656e2eba48964a08c1968ffd826b` / `8fe6a95ecf65d9dc7242a675bc3799d421c2aaa25c325823970e8a46ae9a430c`.
- Seq2Seq result/run: `774dc92e7ef6834042769f8f10624a514dd29974873ff16733bc4ef4b97e73c2` / `c0dc9fd0cdfe225fe41d804feb6ad3c8d92acebe98181bda4acf198cc3e76e7d`.
- Total wall time: Transformer 7.221 s; Seq2Seq 3.567 s.

| Role | Transformer | Seq2Seq |
|---|---|---|
| Quality branch | `Phân tích chất lượng nợ cho vay:` | `Phân tích chất lượng nợ cho vay:` |
| STANDARD | `Nơ dủ tiêu chuản` | `Nợ đủ tiêu chuần` |
| SPECIAL_MENTION | `Nợ cần chú ý` | `Nợ cần chủ ý` |
| SUBSTANDARD | `Nợ dưới tiêu chuẩn` | `Nợ dưới tiêu chuẩn` |
| DOUBTFUL | `Nợ nghi ngờ` | `Nợ nghi ngờ` |
| LOSS | `Nợ có khả năng mất vốn` | `Nợ có khả năng mất vốn` |
| Maturity branch | `Phân tích dư nợ theo thời gian:` | `Phân tích dư nợ theo thời gian:` |
| SHORT_TERM | `Nợ ngắn hạn` | `Nợ ngắn hạn` |
| MEDIUM_TERM | `Nợ trùng hạn` | `Nợ trung hạn` |
| LONG_TERM | `Nợ dài hạn` | `Nợ dài hạn` |

Seq2Seq thắng strict maturity ở MBB; cả hai fail strict quality. Case này được giữ là residual/unresolved và là lý do không silent-coerce prediction. Nó không đảo ngược bằng chứng cross-bank 387 + regression 106 nghiêng về Transformer.

## Quy tắc comparison key an toàn

1. Lưu raw transcript UTF-8, normalize NFC và giữ nguyên dấu tiếng Việt.
2. So khớp full accent-preserving semantic aliases là đường accept trực tiếp an toàn.
3. Có thể tạo key bỏ dấu để shortlist candidate; key này một mình tuyệt đối không được accept.
4. Downstream chỉ có thể promote một accentless candidate nếu role là duy nhất, không collision và có đủ independent topology: owner, branch, ordered siblings, axes, unit, value, total và closure.
5. Scorer hiện tại không thực hiện promotion đó; metric 3/3 chỉ là diagnostic shortlist.
6. Nếu nhiều role va chạm hoặc còn ambiguity trên key bỏ dấu, giữ `UNRESOLVED`; không fuzzy/nearest-role, không chọn theo thứ tự.

Ví dụ `No du tieu chuan` có thể shortlist `Nợ đủ tiêu chuẩn`, nhưng không tự động trở thành `STANDARD`. Chỉ local graph độc lập, đầy đủ và không collision mới có thể promote candidate này. Điều đó vừa cứu recall do OCR mất dấu, vừa ngăn silent coercion sai accounting role.

## Artifact/API tái lập

- Truth UTF-8 hậu-freeze: `docs/experiments/vietocr-transformer-seq2seq-postfreeze-truth-v1.json`.
- Scorer: `src/bctc_ai/evaluation/vietocr_architecture_comparison.py`.
- Runner: `scripts/experiments/compare_vietocr_transformer_seq2seq.py`.
- Generated JSON: `output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run/postjoin/architecture_comparison.json`.
- Generated UTF-8 TXT: `output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run/postjoin/architecture_comparison_utf8.txt`.

Scorer từ chối chạy nếu một trong sáu hash input drift, hai output không complete/reference-blind, crop denominator không đủ 387 all-LINE, config không phải official VietOCR 0.3.13 architecture tương ứng, hoặc truth không bind chính xác cả hai frozen outputs.
