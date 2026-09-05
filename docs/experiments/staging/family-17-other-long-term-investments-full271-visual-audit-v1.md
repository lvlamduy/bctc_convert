# Family 17 — full271 visual audit ledger v1

Scope is the immutable 2025–2026 corpus only. No provider was called and no
source PDF or page JSON was changed.

## Reproducible inputs and result

- Corpus index: `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
- Immutable page store: `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`
- Root pre-audit sweep: `/dev/shm/family17-root-preaudit-v1.json` = 107 R / 53 N / 44 U / 332 mappings on the 204-document expansion.
- Union pre-audit sweep: `/tmp/family17-full271-previsual.json` = 142 R / 76 N / 53 U / 431 mappings.
- Final union sweep: `/tmp/family17-full271-final3.json` = 195 R / 76 N / 0 U / 582 mappings.
- Final audit: `/tmp/family17-full271-final3.audit.json`; audit id `gjfoltieav1:audit:748ca92c7eecbfe8bdf0ce3c2254dd91bdaeee159ce59e331dbaaddbf527017e`.
- All 53 union U documents became R. All 76 pre-audit N documents stayed N.
- Expansion comparator receipt authenticated both old8 oracles (16 source PDFs), proved exact zero SHA overlap with full271, and validated 271 trial / 195 candidate / 195 replay / 14,945 selected-page axes.
- Strict old8 regression (release-pin assertion disabled only because this is a
  changed experimental spec): `/tmp/family17-old8-strict-regression-final.json`
  = 140 R / 0 N / 0 U / 434 mappings. Its comparator retained all 57/57 exact
  historical values; audit id
  `gjfoltieav1:audit:4556a3cfb950424c0471f40a2bc43f0b6f338d979dc8a089f7c39bff8f55301d`.

`Page` below is the source PDF page rendered directly from the SHA-bound file.
`Core` means the file was one of the 44 U documents in the 204-document root
pre-audit; `union` is one of nine additional U documents in full271.

Finding codes:

- `A`: exact OTHER/provision disclosure; a subsidiary-inclusive broad total is deliberately not mapped.
- `B`: two-period cost/provision columns require role-specific metric lanes.
- `L`: exact `Đầu tư dài hạn khác` owner plus alternate OTHER alias and ordinary period handling.
- `N`: exact NAB OTHER alias; `N97` is owner-scoped anonymous investees, `N98` is reset then owner within one narrative section.
- `V`: NVB summary/detail continuation; subsidiary-inclusive broad total is deliberately not mapped.
- `P`: anonymous investee rows with exact gross/provision/net controls below an explicit owner.
- `S`: organization-cost/net detail, long provision alias, unit/continuation inheritance.
- `T`: STB disclosure; `T204` also requires non-money policy exclusion and prevention of titleless income-table context leakage.
- `C`: TCB split unit header and role-specific population; associate-inclusive broad total is deliberately not mapped.
- `W`: VAB alternate aliases / group-row owner / exact mixed-unit owner-row corroboration; subsidiary-inclusive broad total is deliberately not mapped.

## Every initially unresolved file/page

| Full ordinal | Core | Source PDF | Page | Visual finding | Final |
|---:|:---:|---|---:|---|:---:|
| 1 | yes | `vietstock_bctc/ABB/2025/1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf` | 47 | A | R |
| 2 | yes | `vietstock_bctc/ABB/2025/3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf` | 46 | A | R |
| 17 | union | `vietstock_bctc/BAB/2025/BCTC Hop nhat 2025_Kiem toan.pdf` | 28 | B | R |
| 20 | yes | `vietstock_bctc/BAB/2025/BCTC Rieng le 2025_Kiem toan.pdf` | 28 | B | R |
| 22 | union | `vietstock_bctc/BAB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf` | 26 | B | R |
| 69 | yes | `vietstock_bctc/LPB/2025/BCTC 31.12.2025 VN color.pdf` | 43 | L | R |
| 71 | yes | `vietstock_bctc/LPB/2025/BCTC Q3.2025 VN.pdf` | 42 | L | R |
| 73 | yes | `vietstock_bctc/LPB/2025/BCTC quý 1 năm 2025.pdf` | 41 | L | R |
| 74 | union | `vietstock_bctc/LPB/2025/BCTC quý 2 năm 2025.pdf` | 42 | L | R |
| 75 | yes | `vietstock_bctc/LPB/2026/BCTC quý 2 năm 2026.pdf` | 42 | L | R |
| 95 | yes | `vietstock_bctc/NAB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf` | 29 | N | R |
| 96 | yes | `vietstock_bctc/NAB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf` | 29 | N | R |
| 97 | yes | `vietstock_bctc/NAB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 46 | N97 | R |
| 98 | union | `vietstock_bctc/NAB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 43 | N98 | R |
| 100 | yes | `vietstock_bctc/NAB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf` | 28 | N | R |
| 103 | yes | `vietstock_bctc/NAB/2025/NAB namabank_2025_q4_bctc-hn.pdf` | 28 | N | R |
| 104 | yes | `vietstock_bctc/NAB/2026/BCTC Công ty mẹ quý 1 năm 2026.pdf` | 27 | N | R |
| 105 | yes | `vietstock_bctc/NAB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf` | 27 | N | R |
| 106 | yes | `vietstock_bctc/NAB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf` | 27 | N | R |
| 107 | yes | `vietstock_bctc/NAB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf` | 27 | N | R |
| 109 | yes | `vietstock_bctc/NVB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | 33, 34 | V | R |
| 112 | yes | `vietstock_bctc/NVB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 33, 34 | V | R |
| 117 | yes | `vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf` | 32, 33 | V | R |
| 118 | union | `vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf` | 32, 33 | V | R |
| 121 | union | `vietstock_bctc/NVB/2026/4_nvb_2026_5_4_fbaa039_vi_baocaotaichinh_riengle_q1_2026_signed.pdf` | 34, 35 | V | R |
| 140 | yes | `vietstock_bctc/PGB/2025/3_pgb_2025_10_22_8eac562_vi_baocaotaichinh_q3_2025.pdf` | 30 | P | R |
| 141 | yes | `vietstock_bctc/PGB/2025/4_pgb_2026_1_22_d793078_vi_baocaotaichinh_q4_2025.pdf` | 30 | P | R |
| 144 | yes | `vietstock_bctc/PGB/2025/BCTC quý 1 năm 2025.pdf` | 30 | P | R |
| 145 | yes | `vietstock_bctc/PGB/2026/1_pgb_2026_4_28_15bbc70_vi_baocaotaichinh_q1_2026.pdf` | 30 | P | R |
| 146 | yes | `vietstock_bctc/PGB/2026/2_pgb_2026_7_22_3a0f521_vi_baocaotaichinh_q2_2026.pdf` | 30 | P | R |
| 147 | yes | `vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf` | 25, 26 | S | R |
| 148 | union | `vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-4---20205.pdf` | 26, 27 | S | R |
| 149 | yes | `vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf` | 25, 26 | S | R |
| 150 | yes | `vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf` | 26, 27 | S | R |
| 151 | union | `vietstock_bctc/SGB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf` | 22, 23 | S | R |
| 152 | yes | `vietstock_bctc/SGB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf` | 22, 23 | S | R |
| 153 | yes | `vietstock_bctc/SGB/2025/BCTC-hop-nhat-da-duoc-kiem-toan-2025.pdf` | 29, 30 | S | R |
| 154 | yes | `vietstock_bctc/SGB/2025/BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf` | 29, 30 | S | R |
| 155 | yes | `vietstock_bctc/SGB/2025/BCTCBNHN.pdf` | 30, 31 | S | R |
| 156 | yes | `vietstock_bctc/SGB/2025/BCTCBNRL.pdf` | 30, 31 | S | R |
| 157 | yes | `vietstock_bctc/SGB/2026/5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf` | 25, 26 | S | R |
| 158 | yes | `vietstock_bctc/SGB/2026/7_sgb_2026_7_27_a0f7e4f_vi__bao_cao_tai_chinh_q22026_daky.pdf` | 25, 26 | S | R |
| 159 | yes | `vietstock_bctc/SGB/2026/BCTC-HN-quy-1---2026_VIE_0001.pdf` | 25, 26 | S | R |
| 160 | yes | `vietstock_bctc/SGB/2026/BCTC-Rieng-le-quy-1---2026_VIE.pdf` | 25, 26 | S | R |
| 195 | yes | `vietstock_bctc/STB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf` | 31 | T | R |
| 204 | yes | `vietstock_bctc/STB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf` | 21, 31, 35 | T204 | R |
| 219 | yes | `vietstock_bctc/TCB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf` | 49 | C | R |
| 241 | yes | `vietstock_bctc/VAB/2025/20250815 - VAB - BCTC HN BAN NIEN 2025_0001.pdf` | 32 | W | R |
| 242 | union | `vietstock_bctc/VAB/2025/20250815 - VAB - BCTC RIENG LE BAN NIEN 2025_0001_0001.pdf` | 32 | W | R |
| 245 | yes | `vietstock_bctc/VAB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | 33 | W | R |
| 249 | yes | `vietstock_bctc/VAB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 33 | W | R |
| 251 | yes | `vietstock_bctc/VAB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf` | 36 | W; the PDF itself contains a duplicated primary/note value conflict, so only the exact note rows are mapped and the broad population total is suppressed | R |
| 255 | yes | `vietstock_bctc/VAB/2026/BCTC Q1.2026 RIENG LE_0001.pdf` | 35 | W | R |

## Typed-control visual verification

The 27 N rows below were formerly unresolved before the typed subsidiary-only
control. Each reviewed page contains only subsidiary-investment values and/or
dash-only non-subsidiary lines. Therefore no positive OTHER_LONG_TERM_INVESTMENTS
population with a schema mapping exists. Two VBB provision-only positive
controls are listed last and remain R, proving the exclusion is not a blanket
bank/table suppression.

| Full ordinal | Source PDF | Reviewed page(s) | Concrete visual disposition | Final |
|---:|---|---:|---|:---:|
| 24 | `vietstock_bctc/BVB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf` | 3, 26 | subsidiary-only / other roles dash | N |
| 25 | `vietstock_bctc/BVB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf` | 3 | subsidiary-only / other roles dash | N |
| 26 | `vietstock_bctc/BVB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf` | 3 | subsidiary-only / other roles dash | N |
| 31 | `vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhRiengLe_Q2_2025.pdf` | 3, 26 | subsidiary-only / other roles dash | N |
| 32 | `vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhRiengLe_Q3_2025.pdf` | 3, 26 | subsidiary-only / other roles dash | N |
| 36 | `vietstock_bctc/BVB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf` | 5 | subsidiary-only / other roles dash | N |
| 40 | `vietstock_bctc/EIB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 34 | subsidiary-only / other roles dash | N |
| 58 | `vietstock_bctc/KLB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 8 | subsidiary-only / other roles dash | N |
| 61 | `vietstock_bctc/KLB/2025/VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf` | 7 | subsidiary-only / other roles dash | N |
| 125 | `vietstock_bctc/OCB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 49 | subsidiary-only / other roles dash | N |
| 126 | `vietstock_bctc/OCB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf` | 4, 23 | subsidiary-only / other roles dash | N |
| 127 | `vietstock_bctc/OCB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf` | 4, 23 | subsidiary-only / other roles dash | N |
| 128 | `vietstock_bctc/OCB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf` | 4, 23 | subsidiary-only / other roles dash | N |
| 132 | `vietstock_bctc/OCB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf` | 4 | subsidiary-only / other roles dash | N |
| 133 | `vietstock_bctc/OCB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf` | 4 | subsidiary-only / other roles dash | N |
| 134 | `vietstock_bctc/OCB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf` | 4 | subsidiary-only / other roles dash | N |
| 135 | `vietstock_bctc/OCB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf` | 4 | subsidiary-only / other roles dash | N |
| 136 | `vietstock_bctc/OCB/2026/BCTC Công ty mẹ quý 1 năm 2026.pdf` | 4, 24 | subsidiary-only / other roles dash | N |
| 138 | `vietstock_bctc/OCB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf` | 4 | subsidiary-only / other roles dash | N |
| 139 | `vietstock_bctc/OCB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf` | 4 | subsidiary-only / other roles dash | N |
| 228 | `vietstock_bctc/TPB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf` | 34 | subsidiary-only / other roles dash | N |
| 229 | `vietstock_bctc/TPB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf` | 34 | subsidiary-only / other roles dash | N |
| 260 | `vietstock_bctc/VBB/2025/2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf` | 9, 47 | subsidiary-only / other roles dash | N |
| 261 | `vietstock_bctc/VBB/2025/3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf` | 9, 44 | subsidiary-only / other roles dash | N |
| 263 | `vietstock_bctc/VBB/2025/3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf` | 3, 26 | subsidiary-only / other roles dash | N |
| 269 | `vietstock_bctc/VBB/2026/3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf` | 3, 30 | subsidiary-only / other roles dash | N |
| 270 | `vietstock_bctc/VBB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf` | 5, 32 | subsidiary-only / other roles dash | N |
| 257 | `vietstock_bctc/VBB/2025/000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf` | 18 | positive Family 17 provision row, not subsidiary-only | R |
| 258 | `vietstock_bctc/VBB/2025/1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf` | 17 | positive Family 17 provision row, not subsidiary-only | R |

## Gate conclusion

- No visible positive Family 17 disclosure remains N, U, or source-only among
  the 44 root residuals, nine union-only residuals, or 29 typed-control checks.
- No alias, header layout, continuation, slicing, or unit inheritance residual
  remains.
- Broad totals that visibly include subsidiaries (or, for TCB, associates) are
  intentionally not mapped to the Family 17 root. The exact component rows are
  still mapped.
- The VAB Q4 duplicated primary/note values are preserved as source evidence;
  the resolver does not reconcile them by bank- or value-specific logic.
