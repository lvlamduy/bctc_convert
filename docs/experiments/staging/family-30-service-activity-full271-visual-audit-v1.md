# Family 30 service activity full271 visual-audit ledger v1

This staging ledger records the provider-free selected-JSON/PDF audit and
deterministic replay for SERVICE_ACTIVITY. It authorizes neither canonical
schema export nor production publication.

## Immutable scope and baseline

- Current corpus index:
  /dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json;
  file SHA256
  969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219.
- Authenticated selected-page store:
  /dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3;
  SHA256
  ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.
- Population: 271 source PDFs, all under reporting years 2025 or 2026.
  No provider call, prompt route, re-extraction, or non-current corpus document
  was used for the full271 conclusion.
- Baseline /dev/shm/family30-config-pass1-v1.json was
  141 READY / 79 NOT_OBSERVED / 51 UNRESOLVED, with 1,480 mappings;
  SHA256
  63603067d7c0ec2111fecf1570c20329cbf8715ccedaa90e54eda49c070250dc.

Every candidate-bearing unresolved page was checked against its immutable
selected JSON and exact source PDF. Residuals were divided into two layers:
clear PDF observations blocked by selected-JSON transcription or generic
layout semantics, which must be repaired/mapped, and genuine source
inconsistency, which alone may remain unresolved.

## PDF-visible transcription repairs

The registered artifact is
data/registered/gemini_json_service_activity_source_repairs_v1.json, file
SHA256
cbb72b0483a865032f491294ef385ba8121b44137375d14f3c4a840a0abac13d,
size 28,892 bytes, overlay ID
gjsafav1:overlay:33575846ee64630de7c4fc5bcc906be946a983b04c8558f7189bf1fc533111f3.
It contains 8 page/table repairs, 15 exact money-cell transcriptions and one
exact row-label transcription.

Each repair binds source logical name, source SHA/size/document ID, physical
page, 300-DPI PNG SHA/size/dimensions/page ID, extraction run, stored/base and
effective page hashes, base/effective table hashes, exact row/column/path
before-and-after states, table/cell/row crop bounds and RGB hashes. Repair and
overlay identities are content-derived. The runner re-renders the PDFs and
recomputes every full-page and crop hash before evaluation or persistence.

The exact repaired source observations are:

- BVB Q4 p34: selected null to PDF-visible dash, row Thu phí nghiệp vụ
  chiết khấu, comparative column.
- KLB Q1 p28: selected null to PDF-visible dash, row Cước phí bưu điện về
  mạng viễn thông, comparative column.
- PGB Q4 p38: Thụ từ dịch vụ ngân quỹ to the PDF-visible label Thu từ
  dịch vụ ngân quỹ, plus five selected nulls to five visible comparative
  dashes.
- TCB annual p72, Q3 p62, and Q4 p63: two selected nulls per page to the
  visible comparative dashes for the income/expense insurance rows.
- TPB Q1 p43: selected 1.75.572 to PDF-visible 1.175.572.
- TPB Q4 p49: selected null to the PDF-visible comparative dash.

The independent render replay is 8/8 pages and 16/16 registered crop
observations exact. No blank was changed to zero and no number was recovered
from an equation.

## Structural remediation

The declarative topology adds only exact source-visible aliases observed in
the current corpus. Two apparently malformed spellings are not repair
exceptions: the PGB PDF itself prints ... cho thuê tủ ké, and the TPB PDF
itself prints Dịch ủy thác và đại lý; both are therefore ordinary aliases.

The shared/family adapter boundary handles:

- cumulative-duration governors such as Lũy kế từ đầu kỳ đến, Lũy kế từ
  đầu năm đến cuối kỳ này, and 9 tháng đầu năm without interpreting the
  word đầu as comparative-period evidence;
- an explicit adjacent CONTINUES_ON_NEXT_PAGE /
  CONTINUES_FROM_PREVIOUS_PAGE service table as one equation frontier while
  either inheriting a wholly blank receiver period/unit axis or proving an
  exactly equivalent explicit period axis without mutating either page;
- the config-gated leading-child continuation scope used by KLB and VAB only
  when the immediately preceding root carrier and consecutive receiver prefix
  have the same exact lane order; reversed lanes, multiple eligible owners,
  non-adjacency, and explicit-axis conflicts fail closed;
- the VAB title-only continuation shape only in the F30 adapter: one adjacent
  prior page must contain one exact service owner section title and zero MONEY
  tables, the receiver must declare CONTINUES_FROM_PREVIOUS_PAGE and carry a
  complete local root/period/unit axis, and later reset, duplicate owner, or
  non-adjacent shapes fail closed. The shared coalescer was not widened;
- a document-declared component recovery when an unrelated continuation marker
  would otherwise switch generic routing away from the exact declared service
  graph. Recovery replays only the already-classified document graph and retains
  an exact receipt; a primary-statement-only document remains NOT_OBSERVED;
- an adjacent complementary-parent recovery for a separately titled expense
  table immediately following the selected income owner. It requires exact
  complementary root roles, identical period/unit axes, no intervening reset or
  second candidate, and complete all-lane equations;
- exact primary source-result augmentation for split note parents. The primary
  statement contributes only its printed FAMILY_ROOT_TOTAL control when its
  period/unit axes and root vector exactly match the detailed cluster; it does
  not become a detail population or a source of inferred child values;
- a unitless detailed note only when one or more complete, nonzero, exact
  source-visible FAMILY_ROOT_TOTAL, INCOME_PARENT, or EXPENSE_PARENT controls
  match the same semantic roles in a same-document primary statement and all
  matches imply exactly one canonical visible unit; magnitude, wrong-role
  equality, partial lanes, zero vectors, and conflicting controls are never
  unit evidence. Repeated exact Q1 period vectors are valid corroboration only
  when all repetitions agree on the same role, lane order, and unit;
- the ordinary two-parent root frontier and the BAB source-visible five-net-
  component alternative as mutually exclusive complete alternatives. Each BAB
  net component must close against its immediately bounded income/expense
  source rows in both lanes before the five source-signed net values may close
  the family root; flattened one-segment paths do not authorize a search across
  the next net-parent boundary;
- exclusion of typed Giao dịch với các bên liên quan views from the service
  activity ownership graph; and
- an evidence-only legacy-root fallback for a partial label-only parent. The
  shared evaluator must first prove the printed primary root equation, every
  already-observed note lane must equal the corresponding unique primary parent
  row, and only that raw source row may replace the partial mapping. Blank lanes
  are never filled and equation backsolving is forbidden. The VIB source label
  Thu phí đại lý bảo hiểm is mapped by its exact INCOME_INSURANCE alias under
  the same owner fence; and
- control-only, lane-local arithmetic for a true blank child. The blank lane
  remains BLANK_SOURCE_CELL with coefficient null in the mapping and is
  never imputed or emitted as numeric zero.

## Genuine source inconsistency

NAB company-only annual 2025, document ordinal 92, physical page 60,
prints service-income total 730,010 while the printed children sum to
729,836, a difference of 174. The PDF and frozen selected JSON agree on
those values. This is a source arithmetic conflict, not a JSON/PDF
misalignment, so its unresolved disposition is retained without backsolving.
The comparative lane closes exactly at 951,749, and both source-visible parent
lanes close the printed family root (730,010 - 125,919 = 604,091 and
951,749 - 385,907 = 565,842); neither fact resolves the contradictory current
income-child frontier. Evidence is bound to source SHA256
1d98957325e51258eeb3b41ce7de8d43abd0c5db8080b3167dc794cfc60a89a2,
page image SHA256
ce3a8194ce83163ec504ecff8effa0a77f7c879ad81468f7c1e4465802121cd5,
page JSON version
gfpstorev1:json:51848e43c825383484b459a63d01c4fcc9bc7575e2f673404bce5165ca0d7a50,
and canonical page JSON SHA256
55324aa1e811431ad1b4514d93be19389798e0c6d2a7953f8462d7dfad773fe8.

## Acceptance result

### Historical old140 evidence-safe regression seal

The immutable old140 index is
/tmp/gemini-json-first-corpus-production-v2/artifacts/current-corpus-manifest-indexes/61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3.json,
SHA256
79b80d5729d433d6ae06a03272e2f387b646f8bbf28a92b7941e7d3709444c8f.
The authenticated but non-authoritative historical byte comparator is
/tmp/f30-sweep-v3.json, SHA256
ee3fc0578e74f6a162f1322f266b372bba87da250d0dd70560b222e22d615210,
size 26,512,691 bytes. Its mapping bytes are not a release oracle because they
contain blank-to-zero output, a related-party non-owner mapping, and omitted
source-visible roles. It is used only to bind the historical source axis and
enumerate semantic deltas.

The terminal STRICT_RELEASE run is
/dev/shm/family30-old140-strict-bb319-v2.JUIK9E:

- sweep: SHA256
  7a22d73424f5fd76eac5a2b416c87dc2f0016014e91acfdea328db248949acfd,
  26,286,964 bytes, 68 READY / 72 NOT_OBSERVED / 0 UNRESOLVED,
  872 mappings;
- audit: SHA256
  1b1badcff7fe1cbddc8165ed579672d2982f0681f667ed40f0a6fd8121adcf8c,
  audit ID
  gjf30saeav1:audit:c3022b0a8cdaf15c5225e4bf9371a8627c7408f06f204aa1d2a488860d012ad6;
- strict semantic receipt: SHA256
  fd106dfa97a1cda83de07a6e87ed3e5e2409baa772eb86126dbb108de59bb845,
  receipt ID
  f30srsv1:receipt:e901fd5d0fb1378b2b1cc4e687c02e27f60eae1fe6adca264d96451ae0fa3e85;
- results database: SHA256
  e645ba934d53e4c17f72877fead53ca2ce9e6fe5f0e5033d97af1b5d96782d7d,
  SQLite integrity OK, stored sweep typed-equal to the file, run ID
  gjfafstorev1:run:92ff8ff46ac5f671bf47cfbbe237d0ffcafa5ed2d891e228bd02815b9437e1aa.

The source/status/reason axis is exact for all 140 documents, SHA256
87b16a987cc3d50ae4ad0e4030151b318bb97f4076dfbe5ddd2200f01979d2e3.
The generic historical comparator is 160/160 EXACT: 16 document-disposition
records and 144 mapping-value records, axis SHA256
877ef3a3aa48059abb8014bfeebcbed8e9d59823933d6a293ab288e5033c337f.
The source-observation contract is PASS with 0 violations, 1,744 checked mapping
lanes, 3,488 cells, 8 derived cells, 6 partial mappings, and 6 source-blank
cells.

The strict receipt binds the baseline/current semantic axes, exact source axis,
every changed mapping hash, and the selected current component-region frontier.
Its 50-document delta axis has SHA256
a381c07606fa7b1b8ebea359887a76f80b7bfd42d2d3732165cc7001d015082c.
Across individual mapping changes the exact reason counts are: 145 stable-value
provenance reseals, 37 exact source-row rebindings, 4 source-visible schema-role
additions, 3 blank-zero removals, 2 exact authenticated-owner-frontier
recomputations, and 1 non-owner removal. At the document reason-axis level the
counts are respectively 33, 19, 4, 3, 2, and 1; multi-class documents contribute
to more than one count.

The evidence-safety checks are semantic, not descriptive: an addition must bind
only current selected component regions; a removal must have no source region in
the current owner fence; a stable-value reseal must preserve exact coefficient
and source_text lanes; a blank-zero removal must change only a null-text
blank/inferred zero to a null blank/unobserved lane; an exact row rebound requires
raw integer coefficient plus source text in every observed lane; and a
recomputation accepts only exact authenticated aggregate/source-derived states.
The source-observation contract is rerun before the receipt is accepted. Unit
test
test_strict_semantic_delta_receipt_is_content_derived_and_tamper_evident
recomputes the receipt and rejects a modified reason, so neither the 50-row axis
nor an individual classification can be edited without detection.

The complete 50-document delta axis and reasons are:

| Ordinal | Source | Exact receipt reason axis |
| ---: | --- | --- |
| 19 | BID/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 25 | BID/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 40 | CTG/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 53 | HDB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 59 | HDB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 60 | HDB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 69 | MBB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 70 | MBB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 71 | MBB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 72 | MBB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 73 | MBB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 74 | MBB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 75 | MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 76 | MBB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 77 | MBB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 78 | MBB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 79 | MBB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 80 | MBB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 82 | MBB/2026/BCTC Công ty mẹ quý 1 năm 2026.pdf | BASELINE_BLANK_ZERO_REMOVED_AND_SOURCE_BLANK_PRESERVED; MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 83 | MBB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 84 | MBB/2026/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 85 | MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf | BASELINE_BLANK_ZERO_REMOVED_AND_SOURCE_BLANK_PRESERVED; MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 86 | MBB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 87 | VCB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 92 | VCB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW; MAPPING_RECOMPUTED_FROM_EXACT_AUTHENTICATED_OWNER_FRONTIER; SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED; SOURCE_VISIBLE_SCHEMA_ROLE_ADDED_FROM_AUTHENTICATED_CLUSTER |
| 93 | VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 98 | VCB/2025/BCTC Hợp nhất quý 4 năm 2025.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW; MAPPING_RECOMPUTED_FROM_EXACT_AUTHENTICATED_OWNER_FRONTIER; SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED; SOURCE_VISIBLE_SCHEMA_ROLE_ADDED_FROM_AUTHENTICATED_CLUSTER |
| 106 | VIB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 108 | VIB/2025/BCTC Công ty mẹ Soát xét quý 1 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED; SOURCE_VISIBLE_SCHEMA_ROLE_ADDED_FROM_AUTHENTICATED_CLUSTER |
| 110 | VIB/2025/BCTC Công ty mẹ quý 4 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 114 | VIB/2025/BCTC Hợp nhất Soát xét quý 1 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED; SOURCE_VISIBLE_SCHEMA_ROLE_ADDED_FROM_AUTHENTICATED_CLUSTER |
| 115 | VIB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 118 | VIB/2026/BCTC Công ty mẹ Soát xét quý 1 năm 2026.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 123 | VPB/2025/1-bctc-hop-nhat.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 124 | VPB/2025/2-bctc-rieng-le.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 125 | VPB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 126 | VPB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 127 | VPB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 128 | VPB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf | BASELINE_NONOWNER_MAPPING_REMOVED_BY_CURRENT_OWNER_FENCE; MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW; SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 129 | VPB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 130 | VPB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf | BASELINE_BLANK_ZERO_REMOVED_AND_SOURCE_BLANK_PRESERVED |
| 131 | VPB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 132 | VPB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 133 | VPB/2025/Bctc-hop-nhat-1901.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 135 | VPB/2026/1.-BCTC-hop-nhat.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 136 | VPB/2026/2.-BCTC-rieng-le.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 137 | VPB/2026/3-bctc-hop-nhat-ban-tra-cuu.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 138 | VPB/2026/4-bctc-rieng-le-ban-tra-cuu.pdf | SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED |
| 139 | VPB/2026/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |
| 140 | VPB/2026/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf | MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW |

### Current full271 terminal result

Two independent runs used separate TMPDIR and result databases while all
implementation/config bytes were frozen:

- authoritative:
  /dev/shm/family30-authoritative-bb319-v3.tXqkaT; results database SHA256
  d9880089bde90ef2cfe04bf8edfb0ad8955a34768e775e67e6b125ba58e0e18c;
- differential:
  /dev/shm/family30-differential-bb319-v3.RjXz7u; results database SHA256
  44f093731c48d84f37b3c0fdf21382ffcc9185065baba4ca9ecb4baa53d991e0.

Both exited successfully with 202 READY / 68 NOT_OBSERVED / 1 UNRESOLVED
and 2,150 mappings. Both produced sweep ID
gjfafsv1:sweep:51329371e0f41f2938d39c9e0bbc04aba0ba68495e1300bd51406ef8934f7707,
run ID
gjfafstorev1:run:04bd3089f5c77eb337a4c30e83a2cbc4b46c66ae4670cf95cf37ddc65bbb6142,
and audit ID
gjf30saeav1:audit:7fa00a4f34e3df69d4f95f0a646955bff30e887ddf09d282bca9cbbcd2480b19.
The sweep files are byte-identical, SHA256
7fc304d66a286dde79a1eca140abef13af7b02bf040de228e5f85cbd9f153f93,
size 56,486,601 bytes. The audit files are byte-identical, SHA256
1a96cdd15ef2e46fc71bd99e946876d00def018fa63913967e34f2c98478eb3a,
size 5,287,145 bytes.

Each database passes SQLite integrity, contains one run execution and one
export, and reloads a stored sweep typed-equal to its file. The audit has 202
clusters, 862 equations, 2,150 mappings, 2 period normalizations, 8 authenticated
source repairs, and 25 unit corroborations. All 8 registered repairs were
applied exactly once; expected/applied repair-axis SHA256 is
cd3ead0dd089b006b315fa1d07bd831534bdc465063566b417e39be69aa103f2.
The source-observation contract is PASS with 0 violations, 4,300 checked mapping
lanes, 8,600 cells, 256 derived cells, 4 partial mappings, and 4 source-blank
cells. The only unresolved trial is the documented NAB ordinal 92 source
arithmetic conflict above; there is no retained PDF-clear JSON/alignment error.

### Frozen implementation and verification

The terminal implementation/config refs are:

- shared evaluator
  bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2;
- shared runner
  d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5;
- F30 adapter
  18a3e57cdd82ee70fd65a8b623af8c27077281e4e35561ed0dcf0d3a3437ddd8;
- F30 specialized runner
  aebe828deede243797f3ac551c5fcd2692cbe0a473a7b4e206562898a56b02a4;
- topology
  45c942ca562059f5cb35bacfc24bd5a63e06fd0ff8fec708316338c46f95be07;
- evaluation
  146850080b406e8039d332829806f142d43c4ba2eca6fd6186bc4879024a1632;
- schema binding
  0d5b00b2fed527f77d37e72990a3a6fe285eb7e436438c28c872690a5b4708e7;
- source-repair artifact
  cbb72b0483a865032f491294ef385ba8121b44137375d14f3c4a840a0abac13d;
- historical comparator policy
  9115dc1e2b3a22b613fbd4fd0ecd6d8022b457c7c7fcd096f6ec35d865852d36;
- source-observation contract
  aeafa87f5d53c890d6a3640ca561946cfa5e68f9132b79d5f1fe0c741a2ede8a.

The three F30 test files have SHA256
86f4f0b5031107d88ec6de457e8fef133a6cd89710c7d8f7c58ea85be36929dd,
b3f7069e0a104e01d57d693237f6e42ecf1adc92a0c3921f8057d20202ad771b,
and
5ab52db2776fc245bee59968ef828d7947a7d0a0164cf0137217abd5b112b66b.
The combined suite is 115/115 passing. Ruff and py_compile pass on the adapter,
specialized runner, and all three test files. No provider was called and no
document outside the immutable 2025+ corpora entered either conclusion.
