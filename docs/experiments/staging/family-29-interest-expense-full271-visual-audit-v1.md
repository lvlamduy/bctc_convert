# Family 29 — interest expense full271 visual audit v1

This ledger records the end-to-end audit of Family 29 (`INTEREST_EXPENSE`) on
the immutable 2025–2026 corpus. No provider was called. Source PDFs and the
selected Gemini JSON store were read only. Results are experimental
schema-mapping proposals, not canonical or export authority.

## Authenticated inputs and pre-release census

- Full271 index:
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (422,971 bytes; SHA-256
  `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`).
- Common204 index:
  `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
  (317,566 bytes; SHA-256
  `acc1d08e45e5a05925c434ae1c96fd6bc481a0e6ca61fc9f78e155efca7365b1`).
- Initial full271 sweep:
  `/dev/shm/f29-full271-baseline2.af2SAh/sweep.json` (44,291,971 bytes;
  SHA-256 `ffceb7d07b447137f01457874fcd9d1c2437c9477b5b0c003aceb9a5436f5a4b`).
  It contained 204 READY / 3 NOT_OBSERVED / 64 UNRESOLVED / 985 mappings.
- Declarative pre-adapter probe:
  `/dev/shm/f29-current-probe.e0OFrX/sweep.json` (45,628,990 bytes;
  SHA-256 `2301ef20f0c61fd6102de94b1b010780b38d0d292c56ac504fc8c90cf3be7a14`).
  It contained 229 READY / 0 NOT_OBSERVED / 42 UNRESOLVED / 1,121 mappings.
- The 67-document initial residual render inventory is
  `/dev/shm/f29-pdf-audit-renders/inventory.json` (44,033 bytes; SHA-256
  `27b2f5d98844b3cf7d966c58e0adbb9b230a5a9a029802ebb628bf18c7bbdc3e`).

Historical eight-bank artifacts are a disjoint safety oracle only. They have
zero source-SHA overlap with full271 and are excluded from the current-corpus
conclusion. Comparator policy: `DISJOINT_EXPANSION`.

## Complete PDF gate and remediation census

Every one of the initial 67 N/U source PDFs was rendered and visually audited.
Every residual contains visible Family-29 rows that map to the five declared
component roles and, where printed, the Family-29 total. There is no genuine
absence or source conflict in this family. Two later VAB unit-conflict
residuals (full ordinals 246 and 254) were also inspected directly; both have
the same visible note and primary-statement evidence described below.

The exact initial PDF-audited ordinal axis is `3–12, 16, 18, 41, 46, 49, 50,
61, 62, 69, 71, 73–75, 124–141, 144, 157, 158, 163, 193, 194,
199, 200, 204, 241–245, 247, 248, 250–253, 255–259, 267`. Its bank census is
`ABB 10, BAB 2, EIB 4, KLB 2, LPB 5, OCB 16, PGB 3, SGB 2, SHB 1, STB 5,
VAB 12, VBB 5`. Baseline NOT_OBSERVED ordinals `12, 204, 267` all have visible
Family-29 content and therefore are not accepted as true negatives.

The 42 pre-adapter unresolved documents have these complete, non-overlapping
primary remediation routes:

| Route | Full ordinals | Count | Source conclusion |
|---|---|---:|---|
| Last total in the explicit Family-29 root subtree | ABB 3–12; VBB 256–259 | 14 | The Family total is exact; the following net-interest row is outside the Family-29 subtree |
| Observed-lane exact control with a genuinely blank optional lane | BAB 16,18; PGB 140,144; SGB 157,158 | 6 | A blank is omitted or retained as typed null, never used as zero or backsolved |
| Authenticated PDF-visible money/row transcription repair | EIB 41,46,49,50; PGB 141; SHB 163 | 6 | Printed dashes/rows or an independently corroborated digit are visible; selected JSON is corrupt or truncated |
| Distinct duration suffix after one exact common header prefix | KLB 61,62 | 2 | Both period lanes and the local accepted unit are visible |
| Exact same-document primary-statement unit corroboration | OCB 139; STB 201,204; VAB 243,244,246,247,248,250–255 | 14 | Unitless note total exactly matches one canonical unit on the primary Family-29 result |

The routes have cross-cutting evidence requirements. Some terminal-root
documents also carry PDF-visible dash repairs; VBB 257/259 also contain an
all-blank optional role; and ABB ordinal 6 has one independently rounded
million-VND lane (components `8,515,300`, printed total `8,515,301`) while its
comparative lane is exact. The registered repair axis therefore contains 30
repairs over 19 target sources rather than only the six repair-primary
documents. Rounding is enabled only by the explicit family policy and only for
a scaled display unit; the identical residual in VND remains unresolved.

An additional audit of all 229 already-READY candidates found 41 visible rows
that were consumed by exact equations but not emitted as schema mappings:
16 NAB `Trả lãi thuê tài chính` rows, 12 SHB `Trả lãi huy động` rows, and
13 BAB/BVB exact `Chi phí khác ... hoạt động tín dụng khác` rows. These are
now declarative aliases for finance-lease interest, deposit interest, and
other credit expense respectively. The sole remaining non-root source-only
row is `Thu nhập lãi thuần`, visibly after the Family-29 total and correctly
outside the family subtree.

## Authenticated source repair boundary

`config/families/tm-interest-expense-source-repair-v1.json` contains 30 exact
repairs over 19 target PDFs. An independent pre-run authentication checked:

- 20/20 source PDFs by SHA-256 and byte size (19 targets plus one independent
  SHB corroborating source);
- 20/20 physical-page PyMuPDF RGB 2× PNG render SHA-256 values;
- 20/20 selected page-JSON versions and every target before-image;
- the independent SHB comparative value `12.668.527` at its exact
  source/page/table/row/column locator.

Repair kinds are literal PDF-visible money cells, exact appended source rows,
and one cross-source-corroborated exact money cell. A source/page/table/row/
column or before-image mismatch fails closed. No repair is selected by bank,
filename, year, ordinal, note number, or value.

The visibly blank BAB borrowing-interest row at ordinals 16 and 18 is not
repaired or inferred. The role is omitted because every lane is blank. A
visible dash is source-observed zero; a genuine blank remains typed null;
totals are only corroboration and can never invent a missing child value.

## Unit corroboration boundary

The unit adapter applies only when every selected note fragment is unitless,
there is one complete visible note total, and a same-document primary
`INCOME_STATEMENT` Family-29 row has an exactly equal contiguous period
vector. Matches are collapsed by canonical unit and must leave exactly one
unit. Opposite source presentation signs may corroborate unit magnitude, but
the note's observed sign and values are never altered.

OCB ordinal 139 uses the explicit VND unit on the immediately preceding,
physically contiguous primary-statement page. STB uses its explicit
`triệu VNĐ` primary result. VAB contains both VND and million-VND primary
presentations; only the million-VND coefficients equal the note total, so the
unit is unique without magnitude inference. A missing match, conflicting
canonical units, a non-contiguous preceding page, or an incomplete note total
fails closed.

## Pre-release shared-primitive checkpoint

The first run on frozen evaluator SHA-256
`44f87c00d568f5367c313d48159ff764ee54c3ce3f410825308303397acf0304`
completed source authentication and evaluation but stopped before any store
write at 268 READY / 0 NOT_OBSERVED / 3 UNRESOLVED / 1,386 mappings. The exact
residual axis is KLB ordinals 61 and 62 (their two duration paths share one
exact prefix and differ at the visible `Năm nay` / `Năm trước` suffix), plus
VAB ordinal 248 (an exact page-adjacent continuation whose sibling root
components intentionally have no `within_role`). These are acceptance
fixtures for the shared duration-suffix and continuation compatibility
primitives; they are not accepted terminal residuals.

On the next frozen evaluator, SHA-256
`7e536a96efb141f03149a5d4e1f3cb9df844aeace44ffc9d7276dee34ec1a923`,
the strict run again stopped before any artifact or store write at 270 READY /
0 NOT_OBSERVED / 1 UNRESOLVED / 1,396 mappings. KLB 61 and 62 were READY.
VAB 248 was the sole residual: its two exact continuation fragments were now
both selected, but the visible total on the blank-header receiver was not yet
proven against the root components split across the two fragments. A synthetic
family fixture requires that exact continuation-group equation to prove RNID
1151, while removing only the receiver's `CONTINUES_FROM_PREVIOUS_PAGE` marker
must leave the entire visible population UNRESOLVED with no selected region.
The literal source vectors close without rounding:
`2,818,476 + 127,390 + 40,039 + 0 + 1,794 = 2,987,699` and
`2,415,733 + 509 + 31,263 + 0 + 3,910 = 2,451,415`.

## Declarative acceptance contracts

Family 29 opts into five strict shared policies. Each is rejected by the
compiler when absent from the supported value set:

- `source_total_blank_lane_control_policy` is
  `OBSERVED_LANES_EXACT_REMAINDER_BLANK`: only observed cells participate in
  lane arithmetic; a partial role retains a typed-null sister lane and an
  all-blank role is omitted.
- `family_root_terminal_scope_policy` is
  `LAST_SOURCE_TOTAL_WITHIN_EXPLICIT_FAMILY_ROOT_SUBTREE`: the printed Family
  total is eligible for RNID 1151, while a later `Thu nhập lãi thuần` row is
  outside that population and remains source-only.
- `source_presentation_rounding_policy` is
  `INDEPENDENT_DISPLAY_UNIT_ROUNDING_INTERVAL_ALL_EQUATIONS`: each lane is
  checked independently against the declared display-unit interval. It is
  unavailable for VND (`magnitude_power10=0`) and never changes a component or
  total coefficient.
- `duration_header_path_scope_policy` is
  `DISTINCT_SUFFIX_AFTER_EXACT_COMMON_PREFIX`: duration lanes may be named by
  the distinct terminal suffix only when all full source header paths have one
  exact non-empty common prefix. Ambiguous, duplicate, or prefix-free paths
  remain ineligible.
- `adjacent_continuation_family_root_policy` is
  `EXACT_UNION_OF_DECLARED_ROOT_COMPONENTS_EQUALS_RECEIVER_TERMINAL_TOTAL`:
  only an explicitly marked, physically and selected-page adjacent pair may
  prove the receiver's terminal source total against the complete union of
  declared root components. The generic default is disabled; a blank lane,
  arithmetic mismatch, missing marker, duplicate role, or extra receiver row
  fails closed.

Consumer fixtures include the exact all-blank and dash-plus-blank cases, an
extra post-total net-interest row, the observed ABB `+1` million-VND residual,
and the same residual under VND as a mandatory negative control.

## Terminal release

Both authoritative `DISJOINT_EXPANSION` runs completed on 2026-09-04 UTC with
the frozen shared evaluator SHA-256
`bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`:

| Corpus | Documents | READY | NOT_OBSERVED | UNRESOLVED | Mappings | Equations |
|---|---:|---:|---:|---:|---:|---:|
| full271 | 271 | 271 | 0 | 0 | 1,402 | 273 |
| common204 | 204 | 204 | 0 | 0 | 1,054 | 206 |

The full271 mapping census by RNID is 1151=271, 1152=271, 1153=266,
1154=257, 1155=66, 1156=271. Units are 1,302 `MILLION_VND` and 100 `VND`.
The common204 census is 1151=204, 1152=204, 1153=200, 1154=192, 1155=50,
1156=204, with 974 `MILLION_VND` and 80 `VND` mappings. Full271 contains 266
exact and seven display-rounding-interval equations; common204 contains 200
and six respectively. Rounding never changed a source coefficient.

### Artifacts and durable store

| Artifact | Size (bytes) | SHA-256 |
|---|---:|---|
| `/dev/shm/f29-full271-authoritative.B0v23G/family29.json` | 46,764,410 | `6e046e54e6ca2d7f2f85cd7f3b00ba48a11026266011cf45171708934c1d6650` |
| `/dev/shm/f29-full271-authoritative.B0v23G/family29.audit.json` | 22,318 | `70d91bfa87e92c6449cd0cc5faaf3615e56a97d6ef949fae4da13ea0c1e41ada` |
| `/dev/shm/f29-full271-authoritative.B0v23G/family29.sqlite3` | 76,201,984 | `c1023f808d8423110b3f474ab5a1b8ca98b4ce053f1ba74b7e0178fadee31107` |
| `/dev/shm/f29-common204-authoritative.xNLo9g/family29.json` | 35,600,569 | `3132df7ab8eb85ee7e16923638103ccc029191f408e37f3e8dcb3f8f6144ac83` |
| `/dev/shm/f29-common204-authoritative.xNLo9g/family29.audit.json` | 18,840 | `8c007ee71228cdbc1dc9d3493387be1e9105209fd32e946310ae6ae782cda068` |
| `/dev/shm/f29-common204-authoritative.xNLo9g/family29.sqlite3` | 57,856,000 | `02548caaf5abc287373f220f3c1ef28bf09858fb76534ef4907f8c06e51e7c63` |

Full271 IDs are sweep
`gjfafsv1:sweep:5c9692ee11c2a965738b29dd501b85437fdc2580f8849154a106758c22ff056d`,
audit
`gjiefauditv1:audit:27275f47a34a87e03376834c8a910ea2b584d652e1f1ec98ee5a67f0324dec43`,
and run
`gjfafstorev1:run:402f8a6449ecf91fbc0e52118612a237058fc4ef8bd8d4aed624183f2c3a4923`.
Common204 IDs are sweep
`gjfafsv1:sweep:4400bd2518a254570200784691d67c66a01e585738d01968e32a5b5888b87c9e`,
audit
`gjiefauditv1:audit:e4a077872bfca9f213756ed9ed4ac66c60a634dc68d8143da033b26d66589928`,
and run
`gjfafstorev1:run:36c4a62112fe62edbe74ee2600d1f5ce06e5a4a9d012d9afaa0fdcf828ab42aa`.
Both stores returned `PRAGMA quick_check=ok` and an empty foreign-key check.
The runner rebuilt trials from the immutable source-page database, required
typed equality with the evaluated trials, loaded the stored sweep back, and
required exact typed equality before registering each export.

Full271 authenticated 30 source repairs; its authentication-axis SHA-256 is
`e03bd08043a768790bf7e40b373e7e5ae4e15bdb169fcfe29f431304829b36b8`.
Common204 authenticated its applicable 24 repairs; its axis SHA-256 is
`87307375496a034a7c1b24686a154c2e1980043063cc65c67b94f499d317b45f`.
Query-repair/unit-corroboration counts are 19/62 and 16/51 respectively.

### Semantic, source-observation, and visible-row gates

The 204 common `source_sha256` trials are exact after projecting away only
corpus-relative `document_ordinal` and content-derived mapping IDs. Both
ordered semantic projections have SHA-256
`7c792eabcb4a90048e324c273e756fde500093ac72ee329bf7fa80976de396bf`;
there are zero mismatches, and full271 has exactly 67 additional sources.

The source-observation contract passed with zero violations. Full271 checked
2,804 nested mapping occurrences / 5,608 cells / 28 derived cells;
common204 checked 2,108 / 4,216 / 24. Both have zero partial mappings, zero
mapped source-blank cells, and zero numeric null cells. Genuinely all-blank
roles are omitted; printed dashes remain source-observed zeros.

The selected full271 candidates contain 24 source-only rows: 23 visible
Family-root `GROUP` rows consumed by exact equations and one visible
`Thu nhập lãi thuần` row after the Family-29 terminal total. Common204 has the
corresponding 18 plus one. Both corpora have zero
`unmapped_direct_family_rows` and zero `unproven_conditional_zero_rows`, so no
schema-mappable visible child row is left behind.

VAB ordinal 248 now emits exactly RNID 1151–1156. Its RNID 1151 source ref is
only the receiver TOTAL on physical page 40, `s1:t1:r5`; the sealed
`adjacent_continuation_family_root_receipt` binds prior page 39 `s4:t1`, the
receiver, the ordered five-role component axis, and exact source equation
`gjfoltiev1:equation:9e0b306175a6dda59df48f3306786243acb8c9c5519c64fd77b81a632dbb72f9`.
The missing-marker, arithmetic-mismatch, and true-blank-detail-lane fixtures
all fail closed with zero mappings.

Historical comparator disposition is `NOT_APPLICABLE_DISJOINT_CORPUS`: 271
current sources and 16 authenticated oracle sources have exact overlap zero.
No provider was called during audit or replay.

### Implementation and test seal

- F29 topology/evaluation/schema/source-repair specs:
  `9bf00ae73598f3a8b70012be28d06c3622d388970ac4509903f417fd44fbe125` /
  `925cdae2fc24a68ac34b51381352868caebb1c19a8f9634aa41a9c48b6fc8337` /
  `4492389d4f99fcb65d4237e9229757322a68e02aadf4277aedb55a7f2d8d002e` /
  `89b8a3930fd3cf9601ad0af006741e219052d435ac498f8766a0bf0b82a115e9`.
- F29 adapter/specialized runner:
  `db5c361b05735292eb63057fab1ce1fab006798c14244469cb66df74be584839` /
  `c8e1378b84e3fdf54c7fde33e6ecdecd8c35f2fd7b6f35fdc77aaca69612b035`.
- Shared evaluator/generic runner:
  `bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2` /
  `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.
- F29 evaluator/runner tests:
  `8ef2962b6eb00d8e0989029c48f09c5d89d22d128828f4304ff41ec1a7b51993` /
  `1f3896fd8fbc8a0d63adad4e0f30842d72551e00e7595a7479c6525b02f7a2a7`.

The final F29 focused suite passed 26 tests; Ruff, JSON parsing, Python syntax,
and diff checks passed. The shared owner reported 371 unified tests passing on
the frozen evaluator. Final disposition: every PDF-visible, schema-mappable
Family-29 population in the immutable 2025+ full271 corpus is READY, with no
retained NOT_OBSERVED or UNRESOLVED case.
