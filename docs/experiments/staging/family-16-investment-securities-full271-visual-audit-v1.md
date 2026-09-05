# Family 16 investment securities full271 release ledger v1

This is the durable replay and visual-audit ledger for
`INVESTMENT_SECURITIES`. The release conclusion is limited to the immutable
2025-and-later 271-document corpus. It authorizes no schema export or production
publication. No provider, OCR rerun, source mutation, or non-index document was
used.

## Immutable scope and terminal replay

- Corpus index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`.
  Its identity is
  `gjfccmiv1:index:8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a`;
  it binds 271 documents and 14,945 selected pages.
- Authenticated page store:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`,
  573,145,088 bytes, SHA256
  `ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7`.
- Final sweep:
  `/dev/shm/f16-acceptance-full271-v8-final.VXxHpQ/family16.json`,
  33,549,075 bytes, SHA256
  `fc169f778ed5fdfc87638e14de2bc469b9dc8b03c2709eb87fb29f7a3283881e`.
  Sweep ID is
  `gjfafsv1:sweep:45d0533a50ea26097c2e6615c78f50c8ca7cc5d600dce524566bdb9e9c7de9b9`.
- Terminal census is `271 READY / 0 NOT_OBSERVED / 0 UNRESOLVED`, with
  3,299 mappings.
- Final audit:
  `/dev/shm/f16-acceptance-full271-v8-final.VXxHpQ/family16.audit.json`,
  10,085,529 bytes, SHA256
  `b023b680451a48f6a3582c59c78e69520aec9e50bda76d7683b6ea389f0f5e06`.
  Audit ID is
  `gjfiseav1:audit:dd6910a2b753fc64709cbd52b799f090cdf74b9b47e88fa20a5d8575e04236f1`.
- Audit axes are 271 clusters, 1,741 equations, 3,299 mappings, 3,899
  source-row dispositions, and 271 trial dispositions. Their SHA256 values are
  `7585b779c603e2290d238fd37117a019cb2d16aeb733369a2d40bc17d4643f61`,
  `b98985ca8f79935ebfe0cfea4dfaddeb28163f3c680cda766dedb7b223169e98`,
  `e85f846b1ae03b1363bfb0ae19a498d9475e93f9e647cf7cabdd61bfa1789c0a`,
  `efa107a754f9580beb35e5e654c9b3de3350f3fd5722c4da606729f4aacb217b`,
  and
  `bcd6396c7c73e397078913825412d70ef3285c63e5e55a0f054f3a34f2d0212a`.
- Results database:
  `/dev/shm/f16-acceptance-full271-v8-final.VXxHpQ/results.sqlite3`,
  82,341,888 bytes, SHA256
  `98a0c6f9f63c1224a5d7c7dc187553d9f13f682d238368136c86f9c1b6bf5a87`.
  Its stored byte-bound replay passed; family run ID is
  `gjfafstorev1:run:76d76c415dd525d4227394ed49f8f577c7644275c33288d8d8008d7e332952ea`.
- Comparator policy is `DISJOINT_EXPANSION`. The authenticated eight-source
  oracle and current 271-source axis have zero source-SHA overlap; candidate,
  replay, trial, manifest, and selected-page axes were all validated. No
  historical value comparison is asserted for this disjoint corpus.

## Exhaustive selected-row disposition

Every selected, visible family row is present exactly once on the 3,899-row
audit axis. There is no `UNDISPOSED_*` row.

| Disposition | Rows |
|---|---:|
| `MAPPED_SCHEMA_ROLE` | 3,201 |
| `SOURCE_ACCOUNTING_EQUATION_EVIDENCE` | 517 |
| `SOURCE_VISIBLE_ALL_BLANK_NO_VALUE_OBSERVATION` | 67 |
| `SOURCE_VISIBLE_PARTIAL_BLANK_LANE_NO_VALUE_OBSERVATION` | 3 |
| `SOURCE_ONLY_BELOW_MAPPED_SCHEMA_LEAF` | 45 |
| `SOURCE_ONLY_STRUCTURAL_HEADING_WITH_PLACEHOLDER_CELLS` | 33 |
| `SOURCE_ONLY_STRUCTURAL_PARENT_FOR_MAPPED_SCHEMA_LEAF` | 31 |
| `SOURCE_ONLY_EXACT_DETAIL_DECOMPOSITION_OF_MAPPED_SCHEMA_LEAF` | 2 |

The common `source_observation_mapping_contract_v1` audit passes with zero
violations. It sees 6,598 serialized mapping occurrences because the sweep
contains two authenticated copies of each 3,299-row mapping axis. Those copies
contain 280 partial mappings / 280 typed blank cells, corresponding to 140
unique partial mappings / 140 unique blank lanes. No mapping has all lanes
unobserved, no blank became numeric zero, and no `INFERRED_BLANK*` or
`BLANK_ZERO*` state remains. A visible lane beside a blank lane remains mapped;
the blank lane is exactly `coefficient: null`, `state: BLANK_SOURCE_CELL`.

## Residual-to-release accounting

- The current-corpus baseline
  `/dev/shm/f16-current271-trials-v2.json` was
  `269 READY / 0 NOT_OBSERVED / 2 UNRESOLVED`, with 3,176 mappings. The two
  unresolved sources were VAB ordinals 246 and 253. Their visible
  `HTM_DEBT_GOVERNMENT` labels have two genuinely blank value cells. The final
  replay emits no mapping for either row and records
  `SOURCE_VISIBLE_ALL_BLANK_NO_VALUE_OBSERVATION`; equations do not convert the
  blanks to zero.
- A later diagnostic exposed 12 promoted-summary controls: SSB ordinals
  178/179, TCB ordinals 215/216/217/219/220/223, and VBB ordinals
  260/261/262/264. Across the full corpus, 16 SSB/TCB summary tables are now
  sealed as `SOURCE_ONLY_EXACT_INTERNAL_PROMOTED_SUMMARY_DECOMPOSITION` only
  after their visible details exactly close the terminal control. The four VBB
  summaries are mapped to `QUALITY_STANDARD` only after exact AFS+HTM slice
  decomposition. Nonclosing controls remain fail-closed in symmetric tests.
- Three terminal rows initially carried a local `HTM_TOTAL` label but visibly
  close the structurally comprehensive combined family frontier: NVB ordinals
  112/117 and SHB ordinal 162. Each has an explicit
  `TERMINAL_STRUCTURALLY_COMPREHENSIVE_EXACT_FRONTIER` receipt. Nonterminal and
  nonclosing totals retain the narrow/fail-closed rules.
- Owner-qualified zero-hit inventory is reset-bounded. Direct table owners and
  exact titleless adjacent continuations remain in scope, while a numbered or
  titled unrelated sibling cannot inherit section ownership. Activity
  movements, quality/VAMC declared branches, FX/percentage axes, and listing
  views require typed structural signatures rather than isolated tokens.
- A repeated source role may use a complete presentation to corroborate a
  compatible partial duplicate. This requires one explicit complete row whose
  observed values dominate every partial observation. Conflicting rows and
  merely complementary partial rows are never merged or backsolved.

## PDF-visible review ledger

The PNGs below were rendered locally from the SHA-bound source PDFs. Page
numbers in the replay are physical source pages; a PNG filename may be one PDF
container page higher because of an unnumbered cover. The PNG hashes are
recorded only as reproducible visual-review evidence; mappings remain bound to
selected JSON/source locators, not to these images.

| Full ordinal/source | Reviewed page(s) and PNG SHA256 | Visual finding |
|---|---|---|
| 93, NAB separate half-year 2025, source SHA `67303850e6099f72e1cbe081e4f0ab639688524b6392d1fd057e7048ce559286` | 41–42; `nab-separate-p041.png` `51ece8f1920498386d6c1a26845bd4e44a4ac1860e8804c4a88c3a12c576aa74`; `nab-separate-p042.png` `6782a669dffbf91549e085bc0574a93cd7a88a8f67e265d0d717f606ea029767` | Separate AFS/HTM detail and totals are visible across the continuation; repeated presentation does not double-count. |
| 98, NAB consolidated half-year 2025, source SHA `52acb361740cf754cc73227dad8ac1ecfeee98fa5ee43e1bb01dfed977bccf8b` | 42–43; `nab-consolidated-p042.png` `6e851b593a91ecba3e693ee373995eae0da90d0337c4b14db5c8b9c0b8bd00dd`; `nab-consolidated-p043.png` `d1ef8ded3a7591a34747613601ec5a3f43c05a960d2ca76acd6185ae5f374888` | Consolidated AFS gross/provision/net and HTM continuation are visibly complete and distinct from the separate view. |
| 246, VAB separate Q3 2025, source SHA `ffa4437346494781250e3a18998202d559cb6f70d9823f2a0189b5629aa73781` | 34–35; `vab-2025-q3-rl-p034.png` `fb5b728350a81e3253a600815c9c0b84fa7a819b6072b386ecd6505307d65841`; `vab-2025-q3-rl-p035.png` `8d561eefd0b73b120ca36d7ab3af2a0c1caeb16e491e82e42dfc347104ee7b65` | HTM government cells are visibly blank in both lanes; neighboring HTM/VAMC rows print dashes. The blank role is omitted, while printed dashes remain observed zero. |
| 248/252, VAB consolidated/separate Q2 2025, source SHAs `fc653f4dd792a56ea076938379d7dd25d415471622418b8b9a48af6d000cd852` / `30768f3095999e9d8ca315fd93a49ea25cfc151897e7cda89929be8fb71c1956` | 32–33; `vab-q2-p032.png` `5389a532d38bf2eb2a78dd1661c48994f152145663528ae3484873052540720b`; `vab-q2-p033.png` `47e9aab4328a8d037a9fd0f61802ecc3c089ff7084e07e284a639c2c61165411` | Matching layouts visibly distinguish blank cells from printed dashes/zeros across page continuation and preserve the two-period unit. |
| 253/254, VAB separate/consolidated Q2 2026, source SHAs `db337e1de3e7aab90012dec81ef50467b059ad2c7e6acc07cd52b65166d0617f` / `7fa4a8ff1ae6f7c03a8f8bbd881afa3929d8ff5730f5eb5ef0780ddf08695958` | 34–36; `vab-2026-q2-hn-p035.png` `75d251968c27bf5a38a1561416f794730efc96da8c99b76e2bb31d05e5e30eb3`; `vab-2026-q2-hn-p036.png` `763675e1e6b0899bb227931fe58565b6e3ed664ac3c77590cfdfd601278c858f` | HTM government remains visibly blank, while the next HTM lines print `0`; this is the decisive blank-versus-zero negative. |
| 256/257, VBB consolidated/separate Q1 2025, source SHAs `b7ed875bfe1863d514222f81f2064fad1b7e08d9c8756767141ae264ea022eee` / `c8c9e8f5c5c97f5ef066f15ea96deca177f2de9993b7c51e50dd88219b6fca66` | 17–18; `vbb-q1-p017.png` `83c4d9896fc4b3cf65f07b6ce5c15829d81cd7d74a457713a7e7cc8b3ce17fad` | AFS/HTM gross, provision, family total and quality rows are visibly separated; dash populations are explicit. |
| 266, VBB separate Q3 2025, source SHA `7be124482b96dec4cfb256973174a9518c1d4665218e34548306fc248c5a297b` | 26; `vbb-q3-p026.png` `676eb5e82f69e90a26e539327044e06dddf858669cc2a22d1c60fb1df6cb115c` | Explicit million-VND AFS/HTM rows close their printed totals; the following long-term-investment section is a visible owner reset. |

No positive, visible, schema-mappable Family 16 row remains N, U, source-only,
or undisposed in the full271 release scope.

## Compatibility and verification gates

- Final 204-document checkpoint:
  `/dev/shm/f16-acceptance-current204-v9-final.uKoaWc/family16.json`.
  It is 25,707,930 bytes, SHA256
  `b6a7de27b38539398296cbe92694c11d3b04bfab73516ac3781c848f9e439b68`,
  and is `204 READY / 0 NOT_OBSERVED / 0 UNRESOLVED` with 2,539 mappings.
  Its 3,043-row source-disposition axis has zero undisposed rows. The common
  contract passes with 174 typed partial/null lanes and zero violations. Its
  audit SHA256 is
  `befc2d771d2d3ad7d387a446dc3f443d11c97217430d42f7b19157ccaf28a852`;
  the byte-bound results database SHA256 is
  `241aef82ab4cc4463e3aed94ac6070a39623ac9e16403899ed5c8b775b9bca5c`.
  It was replayed from the immutable checkpoint index with
  `DISJOINT_EXPANSION` and zero oracle overlap.
- Legacy strict safety only:
  `/dev/shm/f16-old140-strict-v8.YvdUpk/family16.json`, 19,222,208 bytes,
  SHA256
  `855ba78576fd9b17299c4d1d32fd1a74560585bf8d05d649706ef06b393ec1f2`.
  It retains all 112/112 exact historical values; historical axis SHA256 is
  `6a5af179170b7e6ca0477632309906091c82b5da2279b665a27515704cadf8fb`.
  The source-observation contract passes with zero violations. Its census is
  135 READY / 5 UNRESOLVED: two HDB Q1 and three VPB interim legacy selected
  presentations remain fail-closed. They are outside the eight-source oracle
  and outside the full271 release conclusion. The strict run is a safety test,
  not an alternate scope conclusion.
- Unit/integration command covering the specialized evaluator and runner,
  indexed wiring, and common source-observation contract: `85 passed`.
- Ruff over the owned Python implementation/tests: pass.
- `git diff --check` over all owned Family 16 paths: pass.

Implementation SHA256 values at the terminal replay boundary:

- evaluator:
  `809e6c11d50e3970f4fff26588a84a62e031fe238a9d6cf2282ac01ff0ca7783`
- evaluation/topology/schema specs:
  `482fb11552d070b152cd4e74a185eacefa5d37351fcd396b03f593a460ea9083`,
  `cca05b0ff1c57412714025d4b10cf56066d43c3bd6d12b1a8722c970e2445409`,
  `b6f81ad0ed2808aff9d2387a03b4819e95d6e6fd07c38e9ce45f8774772f634e`
- specialized runner:
  `38d48ecfd67d3902a3083d2fe14eca8853ed4b83de93fa6e0582ee5485110690`
- evaluator/runner tests:
  `11baa9e6f5b4ec1c30c5fe5c0a7065b663dd283fdc04d7836b4d51fd7d849e11`,
  `e20483f1d8f81726fd19df336cc0761d30182752037ac6274ccb3481b896ec06`
- imported shared customer-deposit/hierarchical/topology/contracts/source-
  observation modules:
  `bab5bcbb8c19c1b264cf5946c60817b283793695686374ae3e43390621d46edf`,
  `3f53529552a01abd8543b648088cda27cb4b1fe492a082399b2f24e8d04eb6da`,
  `7d7846e1a8b15379a1489fce01e1f59a88b9ec0aa7e5ea54e506280fa90758ae`,
  `3f48ee42ffb2d0392f3413632421f324a97bdd1225c9056798342bd0d270f1ad`,
  `aeafa87f5d53c890d6a3640ca561946cfa5e68f9132b79d5f1fe0c741a2ede8a`.
