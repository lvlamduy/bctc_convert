# Family 18 tangible fixed assets full271 release ledger v1

This is the durable human/replay ledger for
`TANGIBLE_FIXED_ASSETS_ROLLFORWARD`. It records a local, provider-free audit
of the immutable 2025-and-later corpus. It authorizes no schema export or
production publication.

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
- Source scope is exclusively the indexed 2025-and-later PDFs. No provider,
  OCR, re-extraction, non-index document, or document-year outside that scope
  was used by the replay.

## Baseline and release result

Baseline artifact:
`/dev/shm/family18-full271-baseline-v3.json`, `26,017,290` bytes, SHA256
`67c3837758830fc8fa99c91501d97640733cd78b8e52604ff76ddb711cf81976`.
Its census was `159 READY / 85 NOT_OBSERVED / 27 UNRESOLVED`, with `1,894`
mappings. The matching baseline audit SHA256 is
`54f9386f6bf21f73816119a146a059683cbcf5534127b3c57b0ef5ec76e09e74`.

Release replay:

- Sweep: `/dev/shm/family18-full271-final-v4.json`, `27,439,518` bytes,
  SHA256 `d1eb7a27f4d34dcc38eb418bf9c492ccba780838a6f7a29cd346e4f41438dbb1`.
- Sweep ID:
  `gjfafsv1:sweep:635c35c2922aae5a6d33861cfb153223a4b6a2b4c22f99f78a677ce285cbf2c9`.
- Census: `183 READY / 85 NOT_OBSERVED / 3 UNRESOLVED`, `2,151`
  mappings.
- Audit: `/dev/shm/family18-full271-final-v4.audit.json`, `2,625,493`
  bytes, SHA256
  `79a28cba4fb08b363b82a026de15723489b54658a5ed87208a02aef003dcd0c5`.
- Audit ID:
  `gjffareav1:audit:5b64a31959594ddfcc623b8c71c1a9c0dff910191d53f1a392e6fbc160558346`;
  disposition `SUCCEEDED`.
- Audit axes: `183` clusters, `2,151` mappings, `3,286` equations, zero
  historical comparator rows. Axis hashes are respectively
  `95f199a23d9cd8baededd77832d33d07dab62976a639c25d7e899f57e08b2fc0`,
  `4000e7e60be84390dffb63bbc0f50f53e05bdaf10c4aa5fe1397e9143ae88014`,
  `2b7f7ca706ef5091901a6ad27ade01d37c705f8ef6570d80a1d153aed373fd9d`,
  and
  `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- Results database: `/dev/shm/f18-full271-final-v4.sqlite3`, `66,445,312`
  bytes, SHA256
  `d1118e4a5067ea9bfaa1ce853dadb1573007f6a5138b4ec37831c28a84462011`.
- Historical policy was explicitly `DISJOINT_EXPANSION`: the authenticated
  16-source oracle axis and 271-source current axis have zero source-SHA
  overlap.

## Exact differential

The source-ordered 271-trial axes are identical. Status transitions are:

- `159 READY -> READY`; their complete mapping arrays are byte-exact.
- `85 NOT_OBSERVED -> NOT_OBSERVED`; mappings and reasons are exact.
- `24 UNRESOLVED -> READY`; these add exactly `257` mappings.
- `3 UNRESOLVED -> UNRESOLVED`; each is retained by source evidence below.
- There is no `READY -> UNRESOLVED`, `READY -> NOT_OBSERVED`, or negative
  promotion.

The 24 positive repairs are ordinals `23, 26, 28, 31, 32, 39, 60, 75, 114,
115, 122, 123, 145, 146, 166, 225, 231, 232, 244, 246, 247, 252, 253, 255`.
Every visible/schema-mappable F18 presentation in this residual set is now
READY.

## Registered PDF-visible cell repair artifact

The family config contains only a content reference. All source-specific
material is isolated in
`data/registered/gemini_json_fixed_asset_source_repair_artifact_v1.json`,
`142,430` bytes, SHA256
`eb48bd24bc124a71c6800bf767118a4b4eadf621de213938d3d5ffa86e47c68c`.
Its overlay ID is
`gjffasrv1:overlay:e6d835cbc922af5359b4a84f421a359754aeaf935c13d7d0f1a7367ea93dff5c`.

The artifact contains ten exact repairs and 184 cells:

| Ordinal | Bank | PDF page | Cells | Repair ID |
|---:|:---:|---:|---:|:---|
| 32 | BVB | 27 | 4 | `gjffasrv1:repair:d2411869c9c624513d2370f23ed8c4dcd3d183d1e262e2bc83a4b6f8f9916ff5` |
| 39 | EIB | 35 | 2 | `gjffasrv1:repair:cbbd184ff6019e07b085c3298c3a9cc12c58f2eece670e6fddbe4df60367ac4a` |
| 60 | KLB | 23 | 19 | `gjffasrv1:repair:b075e144370ae1affce28069f3669a894dd4bc4b197a9153b0e8edf6ee62fe27` |
| 75 | LPB | 43 | 3 | `gjffasrv1:repair:c4c7f4ce3ece2da39017b71b249b3b8c78c298a942eb6aa14945c6657c0d98de` |
| 145 | PGB | 31 | 58 | `gjffasrv1:repair:6d6c5d4a2184629ae33f6450e4ce2d8091fc8cfa639a2e055d11c04a16189438` |
| 146 | PGB | 31 | 42 | `gjffasrv1:repair:850104ff7723b89b2e6d2d9cf4b47710efa5c13c87874f3fdbad834399ec38a6` |
| 175 | SHB | 29 | 36 | `gjffasrv1:repair:a8b55171d5e106007664ec8cfa1d4d2d3f119bd607176e19dc4a63920a82643c` |
| 225 | TPB | 48 | 4 | `gjffasrv1:repair:90bcde65f4c7fbf61d436f0200adbf2308c3524ac500b1a7cd55f8684b2d5245` |
| 231 | TPB | 54 | 8 | `gjffasrv1:repair:941db0d5fb12bb4b125a5d26a35ec0f8f0c986b01d6c7b7dd69a01aff11e847c` |
| 232 | TPB | 47 | 8 | `gjffasrv1:repair:b566d3e5eb4c550e4bd6b0030469646f585073ea30edb0df59b4938642ca74fa` |

Each repair binds the exact source name/SHA/size/document ID, physical page,
300-DPI PNG page ID/image SHA/size/dimensions, extraction run, stored JSON
hash, selected page-version ID, base/effective page hashes, section/table IDs,
base/effective table hashes, exact row hierarchy/label, exact column header,
cell coordinate, before/after typed value, and table/cell crop boxes and RGB
hashes. The compiler recomputes document, page, selected JSON, repair and
overlay identities. Runtime applies repairs only to canonical clones and
rechecks the base page/table/cell and effective table/page hashes.

The review policy is
`TRANSCRIBE_ONLY_PDF_VISIBLE_CELL_TOKENS_NO_EQUATION_BACKSOLVE_NO_BLANK_TO_ZERO_NO_PROVIDER`.
The artifact restores only printed money or dash tokens. It never solves an
equation, invents an absent value, or mutates stored selected JSON. Ordinal
175 deliberately remains unresolved after its faithful visual transcription
because the printed source itself conflicts.

## Generic fixes that do not route on source identity

The release engine handles escaped line breaks, exact grouped-integer money,
Gemini dash annotations, explicit/implicit total columns, leading implicit
cost branches, adjacent-page endpoint fragments, adjacent/trailing owner
scope, ordered endpoint and branch scope, partial visible totals while
preserving blank details, and independent display-unit rounding intervals.
It also binds a date from exactly one explicit `Tại ngày`/`As at` row in the
immediately preceding sibling table only. That last receipt makes ordinal 247
READY without filename, bank, page, or year routing:
`faiptsv1:receipt:f6c706a129a95098c43cbb698d2f595810782c789a4dce9b55c09d4cb9885972`.

`_money(None)` remains `BLANK` with a null coefficient. Optional absent
depreciation can contribute zero only inside a carrying control equation; it
does not emit a depreciation mapping. The NAB single-asset positive and SSB
abbreviated sibling-owner reset negative are sealed by unit tests.

## The only three retained unresolved sources

### Ordinal 117 — NVB half-year 2025 consolidated

- Source SHA256:
  `92f4239c94d2880bc99d0986cc61a580dae7b4a2f52721bf4f47700aded2bb65`.
- Current table is physical page 34, selected version
  `gfpstorev1:json:2327e58bafe21ea18e72b260c12c431a4067a5f27ba23e6e0bab26f4b36f66e0`,
  page ID
  `gfpstorev1:page:01dab6c9903c435d105bce2bd8d7438cd2af450ba6285c1a1231a99ccb4fc150`,
  image SHA256
  `17e11cc2eafa9930dffb0ced2c6a0d60fde81837d2b6d64a96bf2eb3c5001b79`.
- The embedded scanned page is physically cropped at its right edge. The
  total header is visibly truncated to `Tổn` and total cells to fragments such
  as `39`, `4`, and `(1`; the missing digits do not exist in the source image.
  Page 35 is explicitly the prior-year movement table, not a substitute for
  the cropped current table. Therefore the current total values are genuinely
  indeterminate and no overlay/backsolve is allowed.
- Final reasons:
  `UNIQUE_RIGHT_EDGE_TOTAL_COLUMN_NOT_VISIBLE` and
  `FAMILY_SIGNAL_TABLE_IS_NOT_A_COMPLETE_FIXED_ASSET_PRESENTATION`.

### Ordinal 120 — NVB separate H1 2026

- Source SHA256:
  `b7eb6ab6d207dced305869e716e479b49a8f1f8bd5a50b91ca0a639773d02069`.
- Physical page 33, selected version
  `gfpstorev1:json:a62e44073021a215ed05874d56569821ff86e65a752d9cc2750c6fc22e2718ec`,
  page ID
  `gfpstorev1:page:717bc2962620f0c237dbd10e6991dc55a8cb7d159f4158e9b81689ca23de6ce4`,
  image SHA256
  `97440b1992910dd84cc869fe214d1fe186f1dd92a92701dcda94fe6199360f69`.
- Selected JSON matches the printed PDF. Printed ending depreciation details
  are `19,616 + 93,925 + 39,989 + 2,370 = 155,900`, while the printed total is
  `194,390`: a source delta of `38,490`. The printed carrying details likewise
  total `263,458`, while the printed total is `224,968`, the same `38,490`
  conflict. Both total-level carrying equations close, but the printed detail
  population does not; choosing either side would infer away source evidence.
- Final reason: `NO_ALL_EQUATION_CLOSING_PROJECTION`.

### Ordinal 175 — SHB consolidated Q1 2026

- Source SHA256:
  `e43e50a17cd71ce393475b2bc53b47d6502b5b966f2d46d17da4dc1eac4cda6f`.
- Physical page 29, selected version
  `gfpstorev1:json:7361bc84e724a655adb893712516e88c0315dfac9aaca5ef168fbf30dcf79449`,
  page ID
  `gfpstorev1:page:6d2bff3e4399838082185066d68a56b782ccb4260a997d7ed534ffd80b3f38a9`,
  image SHA256
  `496351211de70eb2aecbae6938610a4b57f291ad93b6907346a4efab0fbb663b`.
- The authenticated overlay faithfully restores all 36 visibly shifted cells.
  In the `Tài sản cố định khác` depreciation lane, however, the printed
  `Số tăng trong kỳ` subtotal is `+2`, while its printed children are
  `-5 + 3 + 0 = -2`. The difference is `4`, beyond the maximum independent
  million-unit rounding interval of `2`. The printed branch also gives
  `475 + 2 - 15 = 462`, but the printed ending value is `458`; using the
  children gives `458`. This is a genuine PDF subtotal/sign conflict, not a
  selected-JSON alignment error, so no side is silently chosen.
- Final reasons: `VISIBLE_SUBTOTAL_SIGNED_SUM_MISMATCH` and
  `NO_ALL_EQUATION_CLOSING_PROJECTION`.

## Acceptance gates and implementation hashes

- `source_observation_mapping_contract_v1` over the complete release artifact:
  `PASS`, `4,302` duplicated trial/candidate mapping cells audited, `0`
  source blanks, `0` violations. No all-lanes-unobserved or blank-derived
  numeric mapping exists.
- Unit command covering fixed engine, specialized runner, and cross-family
  source-observation contract: `121 passed in 4.55s`.
- `git diff --check` over the owned engine/config/tests/runner paths: pass.
- Fixed-asset engine SHA256:
  `f9dbf30418f21266dfe646e6f4dc13ba94fdacdb27e15f3fad8d25e0fa396a65`.
- Tangible evaluation/topology/schema SHA256:
  `0892e20b0f1cc7384d194825d1e7fc41e1c7f8b8a83ad9378330cb4dabdd6376`,
  `b24ef3506012b0a2f712abaf9791b5d31b1845be671e716f99ab9e2588a54b01`,
  `d9da647690e1a7161d8327badf4035c2565e67fe1a30abe78e5d396443966766`.
- Fixed-asset unit test SHA256:
  `a7121a39e2455ad68afb98fce87202e4ed9ab38f2c559154ccb57b86071ba575`.
- Specialized runner SHA256:
  `0a6a40667b5a0a5ca7abb74fade4b7ef225beec8c1424d6067cfa6680a61f42d`.

The shared fixed-asset engine at the hash above is load-safe for Families 19,
20, and 21.
