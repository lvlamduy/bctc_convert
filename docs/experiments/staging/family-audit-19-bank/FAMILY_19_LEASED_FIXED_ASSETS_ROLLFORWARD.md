# Family 19 leased fixed assets full271 visual-audit ledger v1

This is the durable, provider-free audit ledger for
`LEASED_FIXED_ASSETS_ROLLFORWARD`. It authorizes no schema export or
production publication. The source audit is complete; final replay identities
are recorded only after the shared fixed-asset engine is released by its owner.

## Immutable scope

- Corpus index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (`271` documents, `14,945` selected pages, `422,971` bytes, SHA256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
- Corpus index identity:
  `gjfccmiv1:index:8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a`.
- Authenticated selected-page store:
  `current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`
  (`573,145,088` bytes, SHA256
  `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`).
- Scope is only the indexed 2025-and-later PDFs and their authenticated selected
  JSON. No provider, OCR, re-extraction, source repair, non-index document, or
  equation backsolve was used.

## Human source conclusion

Exactly four indexed documents contain a positive leased-fixed-asset movement
schedule. All four are NAB presentations with one visible `MONEY` asset column,
`Phương tiện vận tải`, in `Triệu đồng`. Because this is the only asset class in
the schedule, that column is the table population and no separate printed
`Tổng cộng` column is required. Both signed branch rollforwards close exactly.

The visible `Giá trị còn lại` rows are exact source controls for
`nguyên giá - khấu hao lũy kế`. Family 19 has no schema role for these rows, so
they corroborate the two endpoints but emit no mapping. This is not a
source-only escape for schema-mappable content.

The release target is `4 READY / 267 NOT_OBSERVED / 0 UNRESOLVED`, with exactly
`30` mappings (`7 + 7 + 8 + 8`).

## Four positive presentations

### Ordinal 92 — separate audited annual 2025

- Source: `vietstock_bctc/NAB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf`.
- Source SHA256:
  `1d98957325e51258eeb3b41ce7de8d43abd0c5db8080b3167dc794cfc60a89a2`;
  source size `18,497,362` bytes.
- PDF page `47`; page JSON
  `gfpstorev1:json:68f7fe9b4b3afe5862acdfe1bd6fbbdcd8bc742755ab4c974d901af0decf1cf0`;
  canonical JSON SHA256
  `c5db824946607a8c9ea6148fedff9e1eba5bdfffff42cc76c237f3bda95c00cc`.
- Page ID
  `gfpstorev1:page:46b1cd69616af51c841d5977b478fef27c48922525e6408050e07f8d1a97d28c`;
  image SHA256
  `32c93ab7ebd0d387551dd5ca7c59006497f73be42f71541b9357f64b31212d7f`.
- Expected mappings: RNID `898=156,859`, `901=-32,200`, `904=124,659`,
  `906=79,173`, `907=23,363`, `909=-28,311`, `912=74,225`.
- Source controls: `156,859 - 32,200 = 124,659`;
  `79,173 + 23,363 - 28,311 = 74,225`; carrying values
  `77,686` and `50,434` equal the corresponding cost-minus-depreciation
  endpoints.

### Ordinal 93 — separate reviewed half-year 2025

- Source:
  `vietstock_bctc/NAB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`.
- Source SHA256:
  `67303850e6099f72e1cbe081e4f0ab639688524b6392d1fd057e7048ce559286`;
  source size `19,349,948` bytes.
- PDF page `45`; page JSON
  `gfpstorev1:json:f569d83684f3a1fa399de99655db59dc1722faab413965ded9720162848f72da`;
  canonical JSON SHA256
  `ce7ef7eddd1721c4c46b07d2b1b63ac4989c3729b44dedbdd70a5ec24ff84daa`.
- Page ID
  `gfpstorev1:page:d852f03668132368dc82b681dd1f1a39ff29e50910d10a6cbb567ad3d8502207`;
  image SHA256
  `4ae00ae114d58e9b4c507a43247a28fe7b1f6e13fb711830ccbafa5b292a9d96`.
- Expected mappings: RNID `898=156,859`, `901=-8,416`, `904=148,443`,
  `906=79,173`, `907=12,689`, `909=-7,628`, `912=84,234`.
- Source controls: `156,859 - 8,416 = 148,443`;
  `79,173 + 12,689 - 7,628 = 84,234`; carrying values
  `77,686` and `64,209` close exactly.

### Ordinal 97 — consolidated audited annual 2025

- Source: `vietstock_bctc/NAB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf`.
- Source SHA256:
  `26287394959f22c6f32c6831eda1e3862c8a73bc917e773d5b2f0ea9ef00afe2`;
  source size `18,456,177` bytes.
- PDF page `48`; page JSON
  `gfpstorev1:json:02e6dc6291cb2a1e3078c68047f91be3f4f74b6df49f0b801c1d1f0244346f70`;
  canonical JSON SHA256
  `bbdd20f38a6c0ab2aa66f6e2bce69660085f9ef53abedfd03612084190e6ed7a`.
- Page ID
  `gfpstorev1:page:55e47a164d5dad99a50356b7375f0505a1c2e8fbfff63e4a8bc5299365003ad7`;
  image SHA256
  `d8ec0475794989be9af29a035dfbb9bd46c733c97d5f89b7f6fcac84645f1869`.
- Expected mappings: RNID `898=159,317`, `899=1,715`, `901=-32,200`,
  `904=128,832`, `906=79,572`, `907=23,953`, `909=-28,311`,
  `912=75,214`.
- Source controls: `159,317 + 1,715 - 32,200 = 128,832`;
  `79,572 + 23,953 - 28,311 = 75,214`; carrying values
  `79,745` and `53,618` close exactly.

### Ordinal 98 — consolidated reviewed half-year 2025

- Source:
  `vietstock_bctc/NAB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`.
- Source SHA256:
  `52acb361740cf754cc73227dad8ac1ecfeee98fa5ee43e1bb01dfed977bccf8b`;
  source size `20,729,238` bytes.
- PDF page `45`; page JSON
  `gfpstorev1:json:e661452a9f544c32a1abb2ebf7b129057fdd38531a5fb6fc54e71d5348a70296`;
  canonical JSON SHA256
  `094fb257f4a0f7558416108f8c2639f8c86488ffaeddbda2b2cf57a17475c0b1`.
- Page ID
  `gfpstorev1:page:ddb861644b3f904f79c1e094083d0b082bde0f1f01a8f32c510130baf5285b3d`;
  image SHA256
  `3817c905c14515bd599fe56ffba08e19722b171c8c036065dd72aad6f00d0018`.
- Expected mappings: RNID `898=159,317`, `899=893`, `901=-8,416`,
  `904=151,794`, `906=79,572`, `907=12,944`, `909=-7,628`,
  `912=84,888`.
- Source controls: `159,317 + 893 - 8,416 = 151,794`;
  `79,572 + 12,944 - 7,628 = 84,888`; carrying values
  `79,745` and `66,906` close exactly.

## PDF-visible audit evidence

Each source page was rendered directly from the SHA-bound PDF at 300 DPI and
inspected visually. The temporary review images are not runtime authorities:

| Ordinal | Render | Bytes | SHA256 |
|---:|---|---:|---|
| 92 | `/dev/shm/separate-audited-p47.png` | 332,588 | `5964f3472bd77cccdcdc0e6f62341cbbeaa5ae6458d08b8073d1500bdd2a4c30` |
| 93 | `/dev/shm/separate-reviewed-p45.png` | 409,061 | `1a8e4bda458a0047cfbfdfa13dfe421bfa07e0fed3b75c323c6ae6c0f625c646` |
| 97 | `/dev/shm/consolidated-audited-p48.png` | 360,228 | `a2d29f8aa0888abc7dcab0ee3ec2d209b314b3aff1cdb069c46c93ec8ff9dc1b` |
| 98 | `/dev/shm/consolidated-reviewed-p45.png` | 415,168 | `dd27074735eec5963aa22b3180d7f5ffbf87da17dd8f75236e398d4412ebcc6b` |

The PDF and selected JSON agree on every owner, branch, asset header, unit,
label, digit, sign, and blank. No source overlay is needed.

## Negative/source-boundary audit

The former common-corpus baseline was `0 READY / 196 NOT_OBSERVED / 8
UNRESOLVED`. Seven of its eight unresolved candidates were false family
captures rather than leased-fixed-asset schedules:

- LPB Q1 2025 pages 42–43: a tangible-fixed-asset schedule continued across
  pages.
- PGB Q1 2025 page 32: an intangible-fixed-asset schedule; the immediately
  preceding leased-fixed-asset disclosure says there was no activity.
- Five SGB reports: the source says
  `Tài sản cố định thuê tài chính: Không phát sinh`, followed by an intangible
  schedule.

The family boundary must return these to `NOT_OBSERVED`, not suppress a
positive leased schedule and not leave a structural false positive unresolved.
The unit suite therefore covers the exact SGB single-section sequence, tangible
and intangible owner resets, finance-lease accounting policy prose, multiple
asset columns without a visible total, an unrecognized single column, branch
equation tampering, and carrying-control tampering.

## Declarative implementation boundary

- `Tăng trong kỳ` and `Tăng trong năm` bind `COST_LEASED_ADDITION` / RNID 899
  only inside the leased cost branch.
- `Chuyển sang tài sản cố định hữu hình` and its abbreviated spelling bind the
  existing economic buyout/transfer roles, RNID 901 and RNID 909, only inside
  their respective branches.
- `Giá trị khấu hao lũy kế` is a depreciation-branch alias.
- `Giá trị còn lại` is declared as an exact, source-only endpoint control and
  never emits a schema mapping.
- A sole recognized asset-class `MONEY` column may serve as the implicit table
  total. The receipt must identify this binding, skip the vacuous horizontal
  identity, and still require both signed vertical equations plus both carrying
  controls.
- No bank, source SHA, filename, page number, value, or ReportNormId appears in
  the generic matching algorithm.

## Final replay acceptance record

The shared fixed-asset engine was released load-safe before the final runs. Its
SHA256 is
`b1a8475812840ca2b07d08a3b40297e237394e9a1fb0cd60b3109845b1fc76ed`.
The final Family 19 implementation boundary is:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `config/families/tm-leased-fixed-assets-topology-v1.json` | 5,560 | `fcc45f599a2df1190e3fad38190f971d7deeb441ce70b58755200773923442a4` |
| `config/families/tm-leased-fixed-assets-evaluation-v1.json` | 3,085 | `c0d51d245d8a1b3586f05067747bf65a25d9b39e49f09c277277e1f6bbbdce34` |
| `config/families/tm-leased-fixed-assets-schema-binding-v1.json` | 1,196 | `39ada7a39e85846a4c5544001e9fdae68bf9b4f59f08cd4c2104dacabee38ead` |
| `src/bctc_ai/evaluation/gemini_json_fixed_asset_rollforward_family_v1.py` | 362,922 | `b1a8475812840ca2b07d08a3b40297e237394e9a1fb0cd60b3109845b1fc76ed` |
| `scripts/experiments/run_gemini_json_fixed_asset_rollforward_accounting_family_v1.py` | 65,015 | `5c1533db7a196d0645b0b48f01cf0ee740f84645f0d6ee93c563f6a50ecb208c` |
| `tests/unit/test_gemini_json_fixed_asset_rollforward_family_v1.py` | 132,383 | `e19a8e019ab8c3035acade51552930d722d9d0574f820e631d5d97b6bfa082f8` |
| `tests/unit/test_gemini_json_fixed_asset_rollforward_indexed_wiring_v1.py` | 26,045 | `be896e0bc0302faddb27e1726b432aa90db67f1bb365d2b3b789c6d352754b9c` |
| `tests/unit/test_run_gemini_json_fixed_asset_rollforward_accounting_family_v1.py` | 11,327 | `ce192c6f7e5c23afbfccc8e2ed7580082b161d7a7c163cf9feedbe43de3b03ed` |
| `tests/unit/test_gemini_json_structural_context_19bank_v1.py` | 372 | `4e8c0c9342776e09d4e9b28161a6dc1ac35510b09af9297a14463759ad3ba028` |

The four-file focused suite passed `142` tests. Ruff passed on the Family 19
runner and indexed-wiring test.

### Full271 replay

Three evaluations produced the same immutable sweep and audit bytes. The first
two establish repeated replay identity; the third was performed after the
final strict-release pin update and therefore captures the final runner
implementation reference. SQLite database bytes intentionally differ because
they authenticate execution and implementation-reference metadata.

- Disposition: `4 READY / 267 NOT_OBSERVED / 0 UNRESOLVED`; mapping count `30`.
- Sweep ID:
  `gjfafsv1:sweep:4fe61c93498c3c65618076b7b7c289282a1a2ce3dfdb90c6c14f2e65400212a4`;
  `7,857,622` bytes; SHA256
  `9d233f2d5f92e081dbc82f91f87d500ec5c3de22b29fd2ade6ae283d81289ac7`.
- Audit ID:
  `gjffareav1:audit:4e5bcb14edf062bc486d876dbc0ed7f3e8ea920594588405d4ecc564628108e1`;
  `27,438` bytes; SHA256
  `e92bc4201387f5620b0d84fc119726b0bdb9d81e7665e6ae59a3584531f7d83d`.
- First two family-run IDs:
  `gjfafstorev1:run:56d596a7bfd73d4136a107af6cf80c09bd4c1edfbb2dd89d7f9bdc4e3b4b7d10`.
  Their `8,597,504`-byte database SHA256 values are respectively
  `9c46e0836a8c763048fe24b4f37a84ad007685140bde4786bb2705fcf8ac8b60`
  and
  `7136436410f862f229364fd96e575fc6d22922063b70ae3e5683a13903fcdf57`.
- Final-code family-run ID:
  `gjfafstorev1:run:3802e2808fbf47bd69b111d2d64722c8228b5b9f545e7a4c02b8a3fd375bf8fc`;
  database `8,597,504` bytes; SHA256
  `ab9dfa6613d2e786e836cde7cc0b7933f72918b2fdcd4e975a5d5ed8bd942943`.
- Audit axes are `4` clusters, `16` equations, `0` historical matches, and
  `30` mappings. Their SHA256 values are respectively
  `4286b3a1fbe334edd6e54bea2ae8f154d068cda0a46426399e0a59daebf3d5c2`,
  `9298ab93db4d4af90933e9c2b07ff098dace1dae25e6414ca83249531c9554e0`,
  `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`,
  and
  `40c4a3404eda2d8f881612198607b1650d6216653889d8c12055aaeafd8ff8f1`.

### Common204 replay

- Disposition: `1 READY / 203 NOT_OBSERVED / 0 UNRESOLVED`; mapping count `8`.
- Sweep ID:
  `gjfafsv1:sweep:cdca7d1156de7e4dea4775ed12b1cb7d0d1b7b0700a55636f00de778b63db36b`;
  SHA256
  `1fd1ab4b8a7b96c1e43cc04aab5bc939eb063a680a5a5efd34cc209cdd0c0574`.
- Audit ID:
  `gjffareav1:audit:0ffe073267b8fecc6ef5019b02a2df819e0473a23d1b2488bc17d41c4912d05f`;
  SHA256
  `5a5af5e9a68ee7f34c30115443eb93ab1d6929e45186d6ba4c41e9ed344192c4`.
- Final-code family-run ID:
  `gjfafstorev1:run:e70905fd1649fbddc8718662a1f82eb49cff1990fbe7e737bda04776ca633cec`;
  database `6,373,376` bytes; SHA256
  `232409b76353bc9e43743fe65e67e7ccc32d477e56f76dbf498e701745048968`.

### Frozen old140 strict-release regression

The official `STRICT_RELEASE` run passed with
`0 READY / 140 NOT_OBSERVED / 0 UNRESOLVED` and zero mappings.

- Sweep ID:
  `gjfafsv1:sweep:553eedc23d9bc34d29560e09bebd583cf78f7463ae4c7bbf7aba5a29c181a74b`;
  SHA256
  `d3daf97d959bdd31ec3bd32e4924d0e9a93bdbfdf6dfcc722275fe9d80c7b38f`.
- Audit ID:
  `gjffareav1:audit:51223d9f18f51b9b7ba87587ec6d4af93a9493aff81dc12d56ec488d57418b45`;
  SHA256
  `f3c838e56e3a5c4894973bf36858b0b754b40a62602750e2467e3883d4057d23`.
- Family-run ID:
  `gjfafstorev1:run:0916b2ad89c1114df0e439af8c41c7c000b6bf58fc6688723cbd95e528c38877`;
  database `4,874,240` bytes; SHA256
  `1726bf151ce95d3eb6269e33a51c259501220e6b4833cf55d84ec845bfd64773`.
- The historical-comparator axis remains exactly `16` rows with SHA256
  `f4f8a10f7deca884492e0423e41d2c4cecd8fd8eadfd281785beac2819dbd1cb`.

The source-observation mapping contract passes with zero violations on
full271, common204, and old140. The sweep representation duplicates selected
mappings under its candidate and trial views (`60`, `16`, and `0` inspected
cells respectively); the release mapping metrics remain `30`, `8`, and `0`.
There are no blank-source cells or partial mappings in any of these Family 19
artifacts. This closes the audited Family 19 target without provider use,
source mutation, inferred blank zero, or residual unresolved disposition.
